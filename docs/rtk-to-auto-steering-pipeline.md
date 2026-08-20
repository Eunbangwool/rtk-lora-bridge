# RTK 보정 데이터 → farmmachine-auto-steering 파이프라인 설계

수신된 RTK 보정 데이터(RTCM3)를 자율조향 앱(`C:\ADB\farmmachine-auto-steering`)의 RTK 입력으로 넣기 위한 설계.

> 이 문서는 소비자 앱(farmmachine-auto-steering)의 소스에 접근할 수 없는 상태에서 작성됐다.
> 정황(경로 `C:\ADB\...`, 이름)상 **AgOpenGPS 계열**(Windows 자율조향, AgIO의 NTRIP 클라이언트로 보정 수신)일
> 가능성이 높다고 보고, 현실적인 수신 방식별로 경로를 제시한다. 실제 앱의 입력 방식을 아래
> [확인 체크리스트](#확인-체크리스트)로 먼저 판별하라.

---

## 1. 확정된 현재 구간 (우리 시스템)

```
[UM980 기지국] ))) 920MHz LoRa ))) [E220+CH340] --USB--> [안드로이드 태블릿]
                                                              │
                                                     RtkLoRaBridge 앱
                                                     ├ UsbLoRaManager (USB에서 RTCM 읽기)
                                                     ├ RtcmFilter (CRC-24Q + 단일 기준국 lock)
                                                     └ NtripCaster  ← 여기서 보정 스트림 제공
                                                        TCP :2101 (NTRIP v1)
```

`NtripCaster` 특성 (코드 기준):
- `ServerSocket(2101)` → **0.0.0.0(모든 인터페이스) 바인딩**. 같은 기기 `127.0.0.1` 뿐 아니라
  **네트워크/USB(ADB)로도 접근 가능**.
- NTRIP v1: 클라이언트가 `GET /<mount> HTTP/1.0` 보내면 `ICY 200 OK` 후 RTCM 바이너리 스트리밍.
- **인증·마운트포인트 검증 없음** (아무 GET 수락). 마운트 이름은 아무거나 써도 됨.
- 단일 기준국(RTK_MSM4) 기반이라 **GGA 상행 불필요**(단방향).

즉 "보정 데이터가 나오는 지점"은 이미 **태블릿의 NTRIP 캐스터 :2101** 로 표준화돼 있다.
남은 일은 이 :2101 을 auto-steering 앱의 RTK 입력에 연결하는 것.

---

## 2. 소비자 앱과의 연결 경로

수신 방식에 따라 세 경로. **경로 A(NTRIP)** 를 기본 권장.

### 경로 A — NTRIP 클라이언트 (권장)

앱(AgOpenGPS면 AgIO)이 NTRIP 클라이언트로 caster 에 접속해 RTCM 을 받는 방식.
우리 캐스터가 바로 그 caster 역할을 한다. **추가 코드 불필요.**

| 분기 | 상황 | 앱의 NTRIP caster 주소 |
|------|------|------------------------|
| **A1** | auto-steering 앱이 **태블릿에서** 실행 | `127.0.0.1:2101` |
| **A2** | 앱이 **PC**에서 실행 + PC–태블릿 **USB 연결** | `adb forward tcp:2101 tcp:2101` 후 **`127.0.0.1:2101`** (USB로 태블릿 캐스터에 터널) |
| **A3** | 앱이 **PC**, 태블릿과 **같은 Wi‑Fi/LAN** | `<태블릿 IP>:2101` |

> 경로 `C:\ADB\...` 는 A2(ADB 포워딩) 정황과 잘 맞는다. → [`tools/adb-ntrip-forward.bat`](../tools/adb-ntrip-forward.bat)

AgIO NTRIP 설정 값:
- Broadcaster IP/URL: 위 표의 주소
- Port: `2101`
- Mount: 아무거나 (예: `RTCM32`) — 우리 캐스터는 무시함
- User/Password: **공란**
- (선택) "Get Source Table" 로 목록 확인 — 최소 소스테이블은 프록시(별도)만 제공하므로,
  태블릿 캐스터 직결 시에는 목록이 비어도 마운트 이름을 직접 입력하면 스트림은 받아진다.
- AgIO는 받은 RTCM 을 **Serial 또는 UDP** 로 GPS 수신기에 전달(기본 둘 다 ON, 쓰는 쪽만 남기기).

### 경로 B — 시리얼 COM 입력

앱이 "RTK/GPS COM 포트"로 RTCM 을 직접 받는 구조라면:
- **PC 브리지**: PC에서 NTRIP 클라이언트가 태블릿 캐스터(:2101, A2/A3)에 접속 → 받은 RTCM 을
  가상 시리얼 포트(`com0com` 등)로 write → 앱이 그 COM 포트를 RTK 입력으로 읽음.
- 또는 태블릿에서 CH340을 통해 다시 시리얼로 내보내는 방식(별도 구현 필요, 비권장).

### 경로 C — TCP/UDP 소켓

앱이 TCP/UDP 로 RTCM 스트림을 받으면:
- TCP: 태블릿 캐스터(:2101, A2/A3)에 직접 연결.
- UDP: 소켓 종류가 다르므로 PC 릴레이(브리지)가 TCP→UDP 변환 필요.

---

## 3. 권장 기본안

```
[태블릿 RtkLoRaBridge NtripCaster :2101]
        │  (USB) adb forward tcp:2101 tcp:2101
        ▼
[PC 127.0.0.1:2101]  ←── farmmachine-auto-steering / AgIO NTRIP 클라이언트
        │  Serial 또는 UDP
        ▼
   [GPS 수신기] → RTK Fix
```

- 앱이 NTRIP 클라이언트(경로 A) 라는 가정 하에 **새 코드 없이** 동작.
- USB 상시 연결이 부담이면 **A3(Wi‑Fi 직결)** 또는 **A1(앱을 태블릿에서 실행)** 로 전환.

---

## 4. 확인 체크리스트

auto-steering 앱(또는 AgIO) 설정에서 아래 중 무엇이 있는지로 경로를 확정:

- [ ] "NTRIP" / "Caster" / "Broadcaster" 입력란 → **경로 A**
- [ ] "GPS COM 포트 / Serial" 로 보정 입력 → **경로 B**
- [ ] "UDP 포트 / 네트워크 GPS" → **경로 C**
- [ ] 앱이 태블릿에서 도는가, PC에서 도는가 → A1 vs A2/A3 결정

---

## 5. 검증 방법

1. (A2) PC에서 `tools\adb-ntrip-forward.bat` 실행 → `adb forward` 확인.
2. PC에서 연결 테스트:
   ```
   # PowerShell 예 (raw 확인)
   $c = New-Object Net.Sockets.TcpClient("127.0.0.1",2101)
   $s = $c.GetStream(); $w=New-Object IO.StreamWriter($s)
   $w.Write("GET /RTCM32 HTTP/1.0`r`n`r`n"); $w.Flush()
   # → "ICY 200 OK" 헤더 후 바이너리(RTCM) 유입되면 성공
   ```
3. AgIO에서 NTRIP 연결 → RTCM 바이트 카운터 증가 확인.
4. 태블릿 앱 UI: **접속 클라이언트 수 증가**, **bytes/s** 확인.

---

## 6. 주의

- `NtripCaster` 는 **인증이 없다.** USB(ADB) 또는 사설 Wi‑Fi 안에서만 노출하고 **공용망에 열지 말 것.**
  다수 고객/인증이 필요하면 `proxy-server/` (계정 풀링·인증)를 앞단에 둘 수 있다.
- `adb forward` 는 USB 연결이 끊기면 함께 끊긴다. 필드 운용은 A1/A3 가 안정적.
- 단일 기준국(RTK_MSM4)이라 GGA 상행은 불필요하지만, AgIO가 GGA 를 올려도 캐스터가 무시하므로 무해.

## 참고

- AgOpenGPS RTK/NTRIP 설정: https://docs.agopengps.com/software/06.-RTK-Setup/ ,
  https://agopengps.gitbook.io/agopengps/frequently-asked-questions/frequently-asked-questions/agio/rtk-ntrip-corrections
