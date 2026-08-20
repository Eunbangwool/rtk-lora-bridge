# RTK LoRa 기지국 브리지 (Orange Pi)

자체 UM980 기지국의 RTCM3 보정 데이터를 920MHz LoRa 로 단방향 브로드캐스트하는 프로그램입니다. **완전 오프라인**(인터넷 불필요).

```
[UM980 GNSS] --UART(/dev/ttyS1)--> base_station.py --UART(/dev/ttyS0)--> [E22 LoRa 송신]
                                                                       )))  920MHz, ~10km
                       [농기계 수신기: E220 + CH340] --USB--> [RtkLoRaBridge 앱] --127.0.0.1:2101--> [CHCNav/FJDynamics]
```

## 왜 커스텀 프로그램인가 (str2str 대비)

단순 중계는 str2str 로도 되지만, 이 프로그램은 다음을 추가로 합니다.

- **기준국 ID 재작성** — 기지국마다 고유 `station_id` 부여. 여러 기지국 커버리지가 겹치는 구역에서 수신기 앱(`RtcmFilter`)이 **하나의 기준국에 lock** 할 수 있게 함. (겹침 대응의 송신 측 절반)
- **메시지 타입 화이트리스트** — LoRa 대역폭에 맞게 필요한 RTCM(MSM4 등)만 송신
- **듀티사이클 제한** — 초당 송신 바이트 상한으로 920MHz 규제 대응
- **상태 모니터링** — 프레임/바이트/CRC오류/드롭 로깅

## 구성 요소

| 파일 | 설명 |
|------|------|
| `base_station.py` | 메인 브리지 (UM980 → 파이프라인 → 듀티제한 → LoRa) |
| `rtcm.py` | RTCM3 파서 + CRC-24Q + 기준국 ID 읽기/재작성 (수신기 `RtcmFilter.kt`와 동일 규약) |
| `um980_config.py` | UM980 기지국 모드 + RTCM 출력 설정 (Unicore 명령) |
| `lora_config.py` | E22 채널/주소/출력 설정 프레임 생성·기록 |
| `config.example.json` | 설정 예시 |
| `base_station.service` | systemd 유닛 |
| `requirements.txt` | pyserial |

## 다중 기지국 설계 (신호 겹침 대응)

여러 기지국을 깔 때 인접 셀이 겹치면 RF 충돌 + 기준국 혼합이 생깁니다. 아래를 **함께** 적용하세요.

| 계층 | 조치 | 어디서 |
|------|------|--------|
| RF | 인접 기지국 **채널 분리** (3채널 재사용, 예: CH70/72/74) | `lora_settings.channel` |
| 논리 | 기지국마다 **고유 station_id** | `station_id` |
| 수신 | 수신기를 가까운 기지국 채널에 맞추고, 앱이 첫 기준국에 lock | 수신기 앱 `RtcmFilter` |

예) 기지국 A: `station_id=1, channel=70(920.125MHz)` / 기지국 B: `station_id=2, channel=72(922.125MHz)`.

## 설정

```bash
cp config.example.json config.json
nano config.json     # station_id, 시리얼 포트, LoRa 채널 등
```

주요 필드:
- `station_id` — 이 기지국의 고유 기준국 ID (1, 2, 3 …)
- `rewrite_station_id` — UM980 출력의 DF003 를 station_id 로 덮어씀(권장 true)
- `source.port` / `lora.port` — UM980 / E22 시리얼 포트
- `rtcm_message_types` — 송신 허용 RTCM 타입(대역폭 절감). `null` 이면 전부 통과
- `max_bytes_per_sec` — 듀티 상한(0=무제한)
- `configure_um980` / `configure_lora` — 시작 시 하드웨어 자동 설정 여부

## 하드웨어 초기 설정 (최초 1회)

### UM980 기지국 모드
```bash
# survey-in(자가측량) 방식
python3 um980_config.py --port /dev/ttyS1 --mode survey
# 또는 알고 있는 고정 좌표
python3 um980_config.py --port /dev/ttyS1 --mode fixed --lat 37.1234567 --lon 127.1234567 --height 45.6
```
기본 출력: 1005 + MSM4(1074/1084/1094/1124) 1Hz + 1033/1230. `SAVECONFIG` 로 저장됩니다.

### E22 LoRa 모듈
E22 는 **설정 모드(M0=1, M1=1)** 에서 9600 8N1 로 설정합니다.
- GPIO 자동 전환: `config.json` 의 `lora_settings.gpio` 에 M0/M1 핀 지정(+ `OPi.GPIO` 설치)
- 수동: M0/M1 을 1/1 로 두고 아래 실행 후 0/0(전송 모드)로 복귀
```bash
python3 lora_config.py --port /dev/ttyS0 --channel 70 --address 0 --power-dbm 30
```

## 실행

```bash
# 로컬 테스트
python3 base_station.py -c config.json

# systemd 등록
sudo cp base_station.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now base_station
journalctl -u base_station -f      # 로그 확인
```

## GPIO 배선 (문서 기준, Orange Pi Zero 2W)

```
UM980 (UART1): Pin8 TX→UM980 RX, Pin10 RX→UM980 TX, Pin4 5V, Pin6 GND
E22   (UART2): Pin19 TX→E22 RXD, Pin21 RX→E22 TXD, Pin2 5V, Pin14 GND
E22 M0/M1: (설정 자동화 시) 여분 GPIO 2개에 연결하고 config gpio 에 핀번호 지정
```

## 주의

- **전파 규정**: 한국 920MHz 대역의 채널/출력/듀티/LBT 규정을 반드시 확인하세요. E22-900T30D 의 1W(30dBm)는 국내 비면허 한도를 초과할 수 있습니다(`power_dbm` 로 낮추거나 인증 모듈 사용).
- Unicore/UM980 명령은 펌웨어 버전에 따라 다를 수 있어 실제 응답 로그로 확인하세요.
- 수신기 측 대응(단일 기준국 lock + CRC 필터)은 `app/` 의 `RtcmFilter.kt` 에 구현돼 있습니다.
