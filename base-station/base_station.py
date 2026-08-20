#!/usr/bin/env python3
"""RTK LoRa 기지국 브리지 (Orange Pi / Linux)

흐름:
    [UM980 GNSS] --UART--> (RTCM3) --> 이 프로그램 --> (RTCM3) --UART--> [E22 LoRa 송신]
                                                                     )))  920MHz 단방향 브로드캐스트
                                                    [농기계 수신기(E220+CH340)] --> RtkLoRaBridge 앱

기능:
    - UM980 시리얼에서 RTCM3 프레임 파싱(CRC 검증)
    - 기준국 ID(DF003) 재작성: 기지국마다 고유 ID 부여 → 여러 기지국 겹칠 때 수신기가 단일 기준국 lock 가능
    - 메시지 타입 화이트리스트: LoRa 대역폭에 맞게 필요한 RTCM만 송신
    - 듀티사이클 제한: 초당 송신 바이트 상한(920MHz 규제 대응)
    - 상태 모니터링/로깅

설정은 config.json 에서 읽는다. config.example.json 참고.
자체 UM980 기지국 방식(완전 오프라인) 전용.
"""

import argparse
import json
import logging
import os
import signal
import time

from rtcm import RtcmReader, set_station_id, message_type, station_id

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("base_station")


class DutyLimiter:
    """이동 1초 창 기준 초당 송신 바이트 상한. 프레임 단위로 통과/폐기 판정."""

    def __init__(self, max_bytes_per_sec: int):
        self.max = max_bytes_per_sec
        self._window_start = None
        self._sent = 0

    def allow(self, nbytes: int, now: float) -> bool:
        if self.max <= 0:
            return True  # 제한 없음
        if self._window_start is None or now - self._window_start >= 1.0:
            self._window_start = now
            self._sent = 0
        if self._sent + nbytes > self.max:
            return False
        self._sent += nbytes
        return True


class RtcmPipeline:
    """수신 바이트 → 완전/유효 프레임 → (타입 필터 + 기준국 ID 재작성) → 송신 프레임 목록."""

    def __init__(self, station_id_value=None, allowed_types=None, rewrite_station=True):
        self.reader = RtcmReader()
        self.station_id_value = station_id_value
        self.allowed_types = set(allowed_types) if allowed_types else None
        self.rewrite_station = rewrite_station and station_id_value is not None
        self.stats_in = 0
        self.stats_out = 0
        self.stats_filtered = 0

    def process(self, chunk) -> list:
        out = []
        for frame in self.reader.push(chunk):
            self.stats_in += 1
            mtype = message_type(frame)
            if self.allowed_types is not None and mtype not in self.allowed_types:
                self.stats_filtered += 1
                continue
            if self.rewrite_station:
                frame = bytes(set_station_id(bytearray(frame), self.station_id_value))
            out.append(frame)
            self.stats_out += 1
        return out


def load_config(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def open_serial(port, baud, timeout):
    import serial  # pyserial (런타임 의존)
    return serial.Serial(port, baudrate=baud, timeout=timeout)


def run(config):
    src = config["source"]        # UM980
    out = config["lora"]          # E22
    st_id = config.get("station_id")
    allowed = config.get("rtcm_message_types")   # None 이면 전부 통과
    rewrite = config.get("rewrite_station_id", True)
    max_bps = int(config.get("max_bytes_per_sec", 0))
    stats_interval = float(config.get("stats_interval_sec", 10))

    # (선택) 하드웨어 초기 설정
    if config.get("configure_um980"):
        try:
            import um980_config
            um980_config.apply(src["port"], int(src["baud"]), config.get("um980", {}))
        except Exception as e:  # noqa: BLE001
            logger.error(f"UM980 설정 실패(계속 진행): {e}")

    if config.get("configure_lora"):
        try:
            import lora_config
            lora_config.apply(out["port"], int(out["baud"]), config.get("lora_settings", {}))
        except Exception as e:  # noqa: BLE001
            logger.error(f"LoRa 설정 실패(계속 진행): {e}")

    pipeline = RtcmPipeline(st_id, allowed, rewrite)
    duty = DutyLimiter(max_bps)

    logger.info(
        f"기지국 브리지 시작: {src['port']}@{src['baud']} → {out['port']}@{out['baud']}, "
        f"기준국 ID={st_id}, 재작성={pipeline.rewrite_station}, "
        f"허용타입={sorted(allowed) if allowed else '전체'}, 상한={max_bps or '무제한'}B/s"
    )

    um980 = open_serial(src["port"], int(src["baud"]), timeout=0.2)
    lora = open_serial(out["port"], int(out["baud"]), timeout=0.2)

    running = {"on": True}
    signal.signal(signal.SIGTERM, lambda *_: running.update(on=False))
    signal.signal(signal.SIGINT, lambda *_: running.update(on=False))

    sent_bytes = 0
    dropped_duty = 0
    last_stats = time.monotonic()

    try:
        while running["on"]:
            chunk = um980.read(4096)
            now = time.monotonic()
            if chunk:
                for frame in pipeline.process(chunk):
                    if duty.allow(len(frame), now):
                        lora.write(frame)
                        sent_bytes += len(frame)
                    else:
                        dropped_duty += 1

            if now - last_stats >= stats_interval:
                logger.info(
                    f"[상태] in={pipeline.stats_in} out={pipeline.stats_out} "
                    f"필터드롭={pipeline.stats_filtered} 듀티드롭={dropped_duty} "
                    f"CRC오류={pipeline.reader.crc_errors} 송신={sent_bytes}B "
                    f"기준국={st_id}"
                )
                last_stats = now
    finally:
        try:
            um980.close()
        except Exception:
            pass
        try:
            lora.close()
        except Exception:
            pass
        logger.info("기지국 브리지 종료")


def main():
    parser = argparse.ArgumentParser(description="RTK LoRa 기지국 브리지")
    parser.add_argument("-c", "--config", default=os.environ.get("BASE_STATION_CONFIG", "config.json"))
    args = parser.parse_args()
    run(load_config(args.config))


if __name__ == "__main__":
    main()
