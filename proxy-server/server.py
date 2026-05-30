#!/usr/bin/env python3
"""NTRIP 프록시 서버 (LG U+ RTK 계정 풀링형)

흐름:
    농기계(NTRIP 클라이언트) → 이 프록시 → LG U+ NTRIP 캐스터

기능:
    - 고객 ID/PW 인증 (SQLite)
    - LG U+ 계정 풀링 (동시 접속 수 = 보유 계정 수)
    - VRS(네트워크 RTK) 대응: 로버가 보내는 GGA(위치)를 상류 캐스터로 전달
    - 사용량 로깅 (과금/통계용)

설정은 config.json 에서 읽는다. config.example.json 참고.
환경변수 NTRIP_PROXY_CONFIG 로 경로 지정 가능 (기본 config.json).
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("ntrip_proxy")

CONFIG_PATH = os.environ.get("NTRIP_PROXY_CONFIG", "config.json")


def load_config(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


@dataclass
class Session:
    customer_id: str
    lgu_account: dict
    connected_at: datetime
    client_addr: str
    bytes_rtcm: int = 0   # 상류 → 농기계 로 보낸 RTCM 바이트
    bytes_gga: int = 0    # 농기계 → 상류 로 보낸 GGA/NMEA 바이트


class AccountPool:
    """LG U+ 계정 풀. 계정 1개 = 동시 접속 1대 제약을 풀링으로 관리."""

    def __init__(self, accounts):
        # 원본 config 를 건드리지 않도록 복사 후 in_use 플래그 부여
        self.accounts = [dict(a, in_use=False) for a in accounts]
        self.lock = asyncio.Lock()

    async def acquire(self) -> Optional[dict]:
        async with self.lock:
            for acc in self.accounts:
                if not acc["in_use"]:
                    acc["in_use"] = True
                    return acc
            return None  # 풀 고갈

    async def release(self, account: dict):
        async with self.lock:
            account["in_use"] = False

    @property
    def in_use_count(self) -> int:
        return sum(1 for a in self.accounts if a["in_use"])

    @property
    def total(self) -> int:
        return len(self.accounts)


class CustomerDB:
    """고객 인증 + 사용량 로깅. sqlite 호출은 블로킹이라 to_thread 로 감싼다."""

    def __init__(self, db_path="customers.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    subscription TEXT DEFAULT 'active',
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    connected_at TEXT,
                    disconnected_at TEXT,
                    bytes_rtcm INTEGER,
                    bytes_gga INTEGER,
                    lgu_account_id TEXT,
                    client_addr TEXT
                )
                """
            )
            conn.commit()

    def _authenticate(self, customer_id: str, password: str) -> bool:
        pw_hash = hashlib.sha256(password.encode()).hexdigest()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT subscription FROM customers WHERE id=? AND password_hash=?",
                (customer_id, pw_hash),
            ).fetchone()
        return row is not None and row[0] == "active"

    async def authenticate(self, customer_id: str, password: str) -> bool:
        return await asyncio.to_thread(self._authenticate, customer_id, password)

    def _log_session(self, session: Session, disconnected_at: datetime):
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO usage_log
                (customer_id, connected_at, disconnected_at,
                 bytes_rtcm, bytes_gga, lgu_account_id, client_addr)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.customer_id,
                    session.connected_at.isoformat(),
                    disconnected_at.isoformat(),
                    session.bytes_rtcm,
                    session.bytes_gga,
                    session.lgu_account["id"],
                    session.client_addr,
                ),
            )
            conn.commit()

    async def log_session(self, session: Session, disconnected_at: datetime):
        await asyncio.to_thread(self._log_session, session, disconnected_at)


class NtripProxy:
    def __init__(self, config: dict):
        self.host = config.get("listen_host", "0.0.0.0")
        self.port = int(config.get("listen_port", 2101))
        up = config["upstream"]
        self.up_host = up["host"]
        self.up_port = int(up["port"])
        self.up_mount = up["mountpoint"]
        self.pool = AccountPool(config["lgu_accounts"])
        self.db = CustomerDB(config.get("db_path", "customers.db"))

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        addr = writer.get_extra_info("peername")
        client_addr = f"{addr[0]}:{addr[1]}" if addr else "?"
        logger.info(f"접속: {client_addr}")

        lgu_account = None
        session = None
        up_writer = None

        try:
            # --- 농기계 요청 라인 + 헤더 파싱 ---
            request_line = await asyncio.wait_for(reader.readline(), timeout=15)
            if not request_line:
                return
            parts = request_line.decode("latin-1", "ignore").strip().split(" ")
            path = parts[1] if len(parts) > 1 else "/"
            mountpoint = path.lstrip("/")

            headers = {}
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=15)
                if line in (b"\r\n", b"\n", b""):
                    break
                if b":" in line:
                    k, v = line.decode("latin-1", "ignore").split(":", 1)
                    headers[k.strip().lower()] = v.strip()

            initial_gga = headers.get("ntrip-gga")  # 일부 클라이언트는 헤더로 첫 GGA 전달

            # --- 소스테이블 요청 (마운트포인트 없이 접속) ---
            if mountpoint == "":
                await self._send_sourcetable(writer)
                return

            # --- 고객 인증 ---
            customer_id, password = self._parse_auth(headers)
            if not customer_id or not await self.db.authenticate(customer_id, password):
                writer.write(
                    b'HTTP/1.1 401 Unauthorized\r\n'
                    b'WWW-Authenticate: Basic realm="NTRIP"\r\n\r\n'
                )
                await writer.drain()
                logger.warning(f"인증 실패: {customer_id!r} from {client_addr}")
                return

            # --- LG U+ 계정 배정 ---
            lgu_account = await self.pool.acquire()
            if not lgu_account:
                writer.write(b"HTTP/1.1 503 Service Unavailable\r\n\r\n")
                await writer.drain()
                logger.warning(f"계정 풀 고갈: {customer_id} (사용중 {self.pool.in_use_count}/{self.pool.total})")
                return

            session = Session(customer_id, lgu_account, datetime.now(), client_addr)
            logger.info(
                f"세션 시작: {customer_id} → {lgu_account['id']} "
                f"({self.pool.in_use_count}/{self.pool.total} 사용중)"
            )

            # --- 상류(LG U+) 연결 ---
            up_reader, up_writer = await asyncio.wait_for(
                asyncio.open_connection(self.up_host, self.up_port), timeout=15
            )
            up_req = (
                f"GET /{self.up_mount} HTTP/1.0\r\n"
                f"User-Agent: NTRIP RtkProxy/1.0\r\n"
                f"Authorization: Basic {self._encode_auth(lgu_account['id'], lgu_account['pw'])}\r\n"
            )
            if initial_gga:
                up_req += f"Ntrip-GGA: {initial_gga}\r\n"
            up_req += "\r\n"
            up_writer.write(up_req.encode())
            await up_writer.drain()

            # 상류 응답 확인
            up_resp = await asyncio.wait_for(up_reader.readline(), timeout=15)
            if b"200" not in up_resp and b"ICY" not in up_resp:
                logger.error(f"상류 연결 실패: {up_resp!r}")
                writer.write(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                await writer.drain()
                return
            # 상류 응답 헤더 소진 (HTTP/1.x 응답일 때)
            if up_resp.upper().startswith(b"HTTP"):
                while True:
                    line = await asyncio.wait_for(up_reader.readline(), timeout=15)
                    if line in (b"\r\n", b"\n", b""):
                        break

            # 농기계에 성공 응답
            writer.write(b"ICY 200 OK\r\nContent-Type: gnss/data\r\n\r\n")
            await writer.drain()

            # --- 양방향 중계 ---
            await self._relay(reader, writer, up_reader, up_writer, session)

        except asyncio.TimeoutError:
            logger.warning(f"타임아웃: {client_addr}")
        except (ConnectionResetError, BrokenPipeError):
            logger.info(f"연결 끊김: {client_addr}")
        except Exception as e:  # noqa: BLE001
            logger.exception(f"오류: {e}")
        finally:
            if up_writer is not None:
                try:
                    up_writer.close()
                except Exception:
                    pass
            if lgu_account is not None:
                await self.pool.release(lgu_account)
            if session is not None:
                await self.db.log_session(session, datetime.now())
                logger.info(
                    f"세션 종료: {session.customer_id}, "
                    f"RTCM {session.bytes_rtcm}B / GGA {session.bytes_gga}B"
                )
            try:
                writer.close()
            except Exception:
                pass

    async def _relay(self, c_reader, c_writer, u_reader, u_writer, session: Session):
        """상류→농기계(RTCM), 농기계→상류(GGA) 동시 중계. 한쪽이 끊기면 종료."""

        async def downstream():  # 상류 → 농기계 (RTCM 보정 데이터)
            while True:
                data = await asyncio.wait_for(u_reader.read(4096), timeout=60)
                if not data:
                    break
                c_writer.write(data)
                await c_writer.drain()
                session.bytes_rtcm += len(data)

        async def upstream():  # 농기계 → 상류 (VRS 용 GGA/NMEA)
            while True:
                data = await c_reader.read(1024)
                if not data:
                    break
                u_writer.write(data)
                await u_writer.drain()
                session.bytes_gga += len(data)

        down = asyncio.create_task(downstream())
        up = asyncio.create_task(upstream())
        done, pending = await asyncio.wait({down, up}, return_when=asyncio.FIRST_COMPLETED)
        for t in pending:
            t.cancel()
        for t in done:
            exc = t.exception()
            if exc and not isinstance(exc, (asyncio.CancelledError, asyncio.TimeoutError)):
                raise exc

    async def _send_sourcetable(self, writer: asyncio.StreamWriter):
        entry = (
            f"STR;{self.up_mount};{self.up_mount};RTCM 3.2;;2;GPS+GLO+GAL+BDS;"
            f"SNIP;KOR;0.00;0.00;0;0;NTRIP RtkProxy;none;B;N;0;\r\n"
        )
        body = (entry + "ENDSOURCETABLE\r\n").encode()
        head = (
            "SOURCETABLE 200 OK\r\n"
            "Server: NTRIP RtkProxy/1.0\r\n"
            "Content-Type: text/plain\r\n"
            f"Content-Length: {len(body)}\r\n"
            "\r\n"
        ).encode()
        writer.write(head + body)
        await writer.drain()

    @staticmethod
    def _parse_auth(headers: dict):
        auth = headers.get("authorization", "")
        if not auth.startswith("Basic "):
            return None, None
        try:
            decoded = base64.b64decode(auth[6:]).decode()
            customer_id, password = decoded.split(":", 1)
            return customer_id, password
        except Exception:
            return None, None

    @staticmethod
    def _encode_auth(user: str, pw: str) -> str:
        return base64.b64encode(f"{user}:{pw}".encode()).decode()

    async def run(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        logger.info(
            f"NTRIP 프록시 시작: {self.host}:{self.port} → "
            f"상류 {self.up_host}:{self.up_port}/{self.up_mount}, "
            f"계정 {self.pool.total}개"
        )
        async with server:
            await server.serve_forever()


def main():
    config = load_config(CONFIG_PATH)
    proxy = NtripProxy(config)
    try:
        asyncio.run(proxy.run())
    except KeyboardInterrupt:
        logger.info("종료")


if __name__ == "__main__":
    main()
