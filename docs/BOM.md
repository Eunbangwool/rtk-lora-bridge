# RTK LoRa 브리지 파일럿 구매 목록
> 파일럿 구성: 브리지 장치 1대 + 농기계 수신기 3대  
> 목적: 논산 상월농산 설치 → AGMO 농기계 테스트

---

## 📦 알리익스프레스 주문 (배송 2~4주)

### 1. LoRa 송신 모듈 (브리지용) × 1개

| 항목 | 내용 |
|------|------|
| 제품 | EByte E22-900T30D V2.0 |
| 역할 | 기지국 LoRa 송신, 1W 출력, 10km |
| 주파수 | 850~930MHz (한국 920MHz 포함) |
| 인터페이스 | UART (라즈베리파이 직결) |
| 알리 검색어 | `EBYTE E22-900T30D` |
| 알리 링크 | https://www.aliexpress.com/item/1005001671012966.html |
| 예상 가격 | $10~13 (약 14,000~18,000원) |
| 수량 | 1개 |

---

### 2. LoRa 수신 모듈 (농기계용) × 3개

| 항목 | 내용 |
|------|------|
| 제품 | EByte E220-900T22D |
| 역할 | 농기계 LoRa 수신, LBT 내장 |
| 주파수 | 850~930MHz |
| 인터페이스 | UART |
| 알리 검색어 | `EBYTE E220-900T22D` |
| 알리 링크 | https://www.aliexpress.com/w/wholesale-EBYTE-E220-900T22D.html |
| 예상 가격 | $4~5 (약 6,000원) × 3 |
| 수량 | 3개 |

---

### 3. USB-UART 변환 보드 × 4개 (여유분 포함)

| 항목 | 내용 |
|------|------|
| 제품 | CH340G USB to TTL UART 모듈 |
| 역할 | LoRa 수신기 → 태블릿 USB 변환 |
| 알리 검색어 | `CH340 USB TTL UART module` |
| 알리 링크 | https://www.aliexpress.com/w/wholesale-ch340-usb-ttl.html |
| 예상 가격 | $1~2 × 4개 |
| 수량 | 4개 |

---

### 4. 920MHz 안테나 세트

| 항목 | 내용 |
|------|------|
| 기지국용 | 5dBi 고이득 안테나 SMA 수커넥터 × 1 |
| 수신기용 | 소형 LoRa 안테나 SMA × 3 |
| 알리 검색어 | `915MHz lora antenna 5dBi SMA` |
| 기지국 링크 | https://www.aliexpress.com/w/wholesale-915mhz-5dbi-antenna-sma.html |
| 수신기 링크 | https://www.aliexpress.com/w/wholesale-915mhz-lora-antenna-sma.html |
| 예상 가격 | 기지국 5,000원 + 수신기 2,000원 × 3 |

---

### 5. Waveshare SIM7600G-H 4G HAT × 1개

| 항목 | 내용 |
|------|------|
| 제품 | Waveshare SIM7600G-H 4G HAT |
| 역할 | 라즈베리파이 LTE 연결 (NTRIP 수신) |
| 호환 | Raspberry Pi Zero 2W 직결 가능 |
| 알리 검색어 | `Waveshare SIM7600G-H 4G HAT` |
| 알리 링크 | https://www.aliexpress.com/w/wholesale-waveshare-sim7600g-h-4g-hat.html |
| 공식 링크 | https://www.waveshare.com/sim7600g-h-4g-hat.htm |
| 예상 가격 | $30~35 (약 42,000~49,000원) |
| 수량 | 1개 |

---

### 6. 소형 방수 함체 × 1개

| 항목 | 내용 |
|------|------|
| 제품 | 알루미늄 IP65 함체 150×100×75mm |
| 역할 | 브리지 장치 방수 보호 |
| 알리 검색어 | `aluminum IP65 enclosure 150x100` |
| 알리 링크 | https://www.aliexpress.com/w/wholesale-aluminum-ip65-enclosure-150x100.html |
| 예상 가격 | $10~15 (약 14,000~21,000원) |
| 수량 | 1개 |

---

### ⚠️ 알리 주문 주의사항

```
1. 주파수 확인
   850~930MHz 포함 여부 필수 확인
   한국 920.9~923.3MHz 커버해야 함

2. UART 버전 확인
   모델명에 'T' 포함 = UART (올바름)
   모델명에 'M' 포함 = SPI (아님)

3. 안테나 커넥터 타입
   SMA-K (SMA 암) 확인
   모듈과 안테나 커넥터 일치해야 함

4. 배송 방법
   급하면 "AliExpress Standard Shipping" 선택
   느려도 되면 "China Post" (무료)
```

---

## 🇰🇷 국내 주문 (빠른 배송)

### 7. Raspberry Pi Zero 2W × 1개

| 항목 | 내용 |
|------|------|
| 제품 | Raspberry Pi Zero 2W |
| 역할 | 브리지 메인 컴퓨터 |
| 구매처 1 | 아이씨뱅큐: https://www.icbanq.com/P013032933 |
| 구매처 2 | 디바이스마트: https://www.devicemart.co.kr/goods/view?no=14253319 |
| 구매처 3 | 엘레파츠: https://m.eleparts.co.kr/goods/view?no=11540752 |
| 예상 가격 | 28,000~35,000원 |
| 수량 | 1개 |

> ⚠️ GPIO 헤더 미납땜 버전과 납땜 버전(WH) 있음  
> Waveshare HAT 연결 위해 **납땜 버전(Zero 2WH)** 권장

---

### 8. MicroSD 카드 32GB × 1개

| 항목 | 내용 |
|------|------|
| 제품 | SanDisk 32GB MicroSD (Class 10) |
| 역할 | 라즈베리파이 OS 저장 |
| 구매처 | 국내 다이소/쿠팡/11번가 |
| 예상 가격 | 8,000~12,000원 |
| 수량 | 1개 |

---

### 9. 태양광 시스템 (브리지 전원)

| 항목 | 규격 | 예상 가격 |
|------|------|-----------|
| 태양광 패널 | 40W 12V | 25,000원 |
| MPPT 충전 컨트롤러 | 10A | 20,000원 |
| LFP 배터리 | 12V 20Ah (인산철) | 60,000원 |
| DC-DC 컨버터 | 12V→5V 3A | 8,000원 |
| 소계 | | 약 113,000원 |

구매처: 옥션/11번가에서 "태양광 패널 40W" 검색  
배터리: 반드시 **LiFePO4(인산철)** 확인 (Li-ion 아님)

---

## 💰 총 예상 비용

### 알리익스프레스
| 품목 | 수량 | 단가 | 소계 |
|------|------|------|------|
| E22-900T30D (송신) | 1 | 16,000 | 16,000 |
| E220-900T22D (수신) | 3 | 7,000 | 21,000 |
| CH340 USB 변환 | 4 | 2,000 | 8,000 |
| 920MHz 안테나 세트 | - | - | 11,000 |
| SIM7600G-H HAT | 1 | 45,000 | 45,000 |
| IP65 함체 | 1 | 17,000 | 17,000 |
| **알리 소계** | | | **118,000원** |

### 국내
| 품목 | 수량 | 단가 | 소계 |
|------|------|------|------|
| 라즈베리파이 Zero 2WH | 1 | 32,000 | 32,000 |
| MicroSD 32GB | 1 | 10,000 | 10,000 |
| 태양광 시스템 | - | - | 113,000 |
| **국내 소계** | | | **155,000원** |

### **총합계: 약 273,000원**

---

## 📅 주문 순서

```
Day 1 (오늘)
└─ 알리 주문 (배송 2~4주 소요)
   E22-900T30D, E220-900T22D × 3
   CH340 × 4, 안테나, SIM7600G-H HAT, 함체

Day 1~3
└─ 국내 주문 (2~3일 내 도착)
   라즈베리파이 Zero 2WH
   MicroSD 32GB
   태양광 세트

Day 3~10
└─ 국내 부품 도착 시
   라즈베리파이 OS 설치
   str2str 소프트웨어 셋업
   앱 개발 병행

Day 14~28
└─ 알리 부품 도착
   전체 조립 및 테스트
   논산 현장 설치
```

---

## 🔗 참고 링크

- EByte 공식 제품 페이지: https://www.cdebyte.com
- Waveshare SIM7600G-H 공식: https://www.waveshare.com/sim7600g-h-4g-hat.htm
- RTKLIB str2str 문서: https://github.com/tomojitakasu/RTKLIB
- usb-serial-for-android 라이브러리: https://github.com/mik3y/usb-serial-for-android
- Raspberry Pi Zero 2W 공식: https://www.raspberrypi.com/products/raspberry-pi-zero-2-w/
