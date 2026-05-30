# NTRIP 프록시 서버

LG U+ RTK 계정을 풀링해서 다수의 농기계(NTRIP 클라이언트)에 보정 데이터를 중계하는 프록시 서버입니다.

```
[농기계 태블릿 CHCNav/FJDynamics]
        │  NTRIP (고객 ID/PW)
        ▼
[이 프록시 서버]  ── 고객 인증 / LG U+ 계정 풀링 / 사용량 로깅
        │  NTRIP (LG U+ 계정)
        ▼
[LG U+ RTK NTRIP 캐스터]  ntrip.lguplus.com:2101
```

"계정 1개 = 동시 접속 1대" 제약을, 보유 계정 N개를 풀로 묶어 **동시 접속 N대**까지 서비스합니다. 농기계가 접속을 끊으면 계정은 풀로 반납됩니다.

## 구성 요소

| 파일 | 설명 |
|------|------|
| `server.py` | 비동기 NTRIP 프록시 (asyncio) |
| `manage_customers.py` | 고객 추가/삭제/조회 CLI |
| `config.example.json` | 설정 예시 (복사해서 `config.json` 작성) |
| `ntrip_proxy.service` | systemd 유닛 |
| `requirements.txt` | 의존성 (표준 라이브러리만 사용 → 비어 있음) |

## 마운트포인트 / GGA (단일기준국 vs VRS)

LG U+ 서버: `3.34.9.182:2101`

- **권장: `RTK_MSM4_RTCM32`** — 단일기준국 방식. **GGA 전송 불필요**, LoRa 단방향 호환. 본 프로젝트 기본값.
- `iMAX_RTCM3.x(MSM4)` 같은 VRS 마운트포인트는 로버 위치(GGA)를 올려야 보정이 내려옵니다.

이 프록시는 **양방향 중계**라 두 방식 모두 지원합니다.

- 상류 → 농기계: RTCM 보정 데이터 (항상)
- 농기계 → 상류: GGA/NMEA 위치 (초기 `Ntrip-GGA` 헤더 + 접속 중 주기 GGA 전달)
  - 단일기준국 마운트포인트에서는 로버가 GGA를 보내지 않으므로 이 경로는 자연히 비활성 — **무해**합니다.

## 설정

```bash
cp config.example.json config.json
# config.json 편집:
#  - upstream.host       : LG U+ 서버 (3.34.9.182)
#  - upstream.mountpoint : LG U+ 마운트포인트 (권장 RTK_MSM4_RTCM32)
#  - lgu_accounts        : 보유한 LG U+ 계정 전부 추가
```

> `config.json` 과 `customers.db` 는 비밀정보라 `.gitignore` 로 커밋에서 제외됩니다.

## 고객 관리

```bash
python3 manage_customers.py add  --id AGMO_001 --pw password123
python3 manage_customers.py list
python3 manage_customers.py disable --id AGMO_001   # 구독 만료 처리
python3 manage_customers.py enable  --id AGMO_001
python3 manage_customers.py remove  --id AGMO_001
```

## 실행

```bash
# 로컬 테스트
python3 server.py            # config.json 사용
NTRIP_PROXY_CONFIG=/path/config.json python3 server.py
```

## 배포 (AWS EC2 / Ubuntu 22.04)

```bash
# 1. 파일 업로드
scp -r proxy-server ubuntu@서버IP:~/ntrip_proxy

# 2. 설정/고객 등록
cd ~/ntrip_proxy
cp config.example.json config.json && nano config.json
python3 manage_customers.py add --id AGMO_001 --pw ...

# 3. systemd 등록
sudo cp ntrip_proxy.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ntrip_proxy
sudo systemctl status ntrip_proxy

# 4. 방화벽/보안그룹: TCP 2101 인바운드 허용
```

## 농기계(고객) 설정

```
NTRIP 서버:  proxy.우리도메인.com
포트:        2101
ID / PW:     고객별 지급
마운트포인트: 위 소스테이블에 노출된 이름 (config 의 upstream.mountpoint 와 동일)
```

## 보안 메모

- 비밀번호는 sha256 해시로 저장됩니다. 운영 강화 시 per-user salt 또는 `bcrypt`/`argon2` 도입을 권장합니다.
- LG U+ 계정 정보(`config.json`)는 서버에만 두고 절대 커밋하지 마세요.
- 가능하면 NTRIP over TLS 또는 신뢰 네트워크 경계 안에서 운용하세요.
