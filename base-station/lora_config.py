#!/usr/bin/env python3
"""EBYTE E22-900T 시리즈 LoRa 모듈 설정.

기지국마다 채널/주소를 지정해 인접 기지국과 겹치지 않게 한다(주파수 재사용).
설정은 모듈을 '설정 모드(M0=1, M1=1)'에 두고 9600 8N1 로 C0 명령을 보낸다.
(설정 모드 UART 속도는 REG0 값과 무관하게 항상 9600 고정)

레지스터(0x00~0x06):
    00 ADDH, 01 ADDL, 02 NETID,
    03 REG0 (UART속도<<5 | 패리티<<3 | 무선속도),
    04 REG1 (서브패킷<<6 | RSSI<<5 | 송신출력),
    05 REG2 (채널 CH; 실제주파수 = 850.125 + CH MHz),
    06 REG3 (RSSI바이트<<7 | 전송방식<<6 | LBT<<4 | WOR)

주파수 예: 920.125MHz = CH 70. 한국 920MHz 대역/출력 규정 확인 필요.

단독 실행(설정 모드로 두고):
    python3 lora_config.py --port /dev/ttyS0 --channel 70 --address 0 --netid 0
"""

import argparse
import logging
import time

logger = logging.getLogger("lora_config")

_UART_BAUD = {1200:0b000, 2400:0b001, 4800:0b010, 9600:0b011,
              19200:0b100, 38400:0b101, 57600:0b110, 115200:0b111}
_AIR_RATE = {300:0b000, 1200:0b001, 2400:0b010, 4800:0b011,
             9600:0b100, 19200:0b101, 38400:0b110, 62500:0b111}
_SUBPACKET = {240:0b00, 128:0b01, 64:0b10, 32:0b11}
# E22-900T30D 기준 송신출력(dBm). T22 모듈은 22/17/13/10 으로 매핑이 다름.
_POWER_30 = {30:0b00, 27:0b01, 24:0b10, 21:0b11}
_POWER_22 = {22:0b00, 17:0b01, 13:0b10, 10:0b11}


def build_config_frame(settings: dict) -> bytes:
    """C0(영구 저장) 설정 프레임 생성. 순수 함수(테스트 가능)."""
    addr = int(settings.get("address", 0)) & 0xFFFF
    netid = int(settings.get("netid", 0)) & 0xFF
    uart = _UART_BAUD[int(settings.get("uart_baud", 115200))]
    parity = 0b00  # 8N1
    air = _AIR_RATE[int(settings.get("air_rate", 9600))]
    subpacket = _SUBPACKET[int(settings.get("subpacket", 240))]
    rssi_ambient = 1 if settings.get("rssi_ambient", False) else 0

    power_map = _POWER_22 if int(settings.get("power_series", 30)) == 22 else _POWER_30
    power = power_map[int(settings.get("power_dbm", max(power_map)))]

    channel = int(settings.get("channel", 70)) & 0xFF
    rssi_byte = 1 if settings.get("rssi_byte", False) else 0
    fixed_tx = 1 if settings.get("fixed_transmission", False) else 0  # 0=투명전송(브로드캐스트)
    lbt = 1 if settings.get("lbt", False) else 0
    wor = int(settings.get("wor_cycle", 0)) & 0b111

    reg0 = (uart << 5) | (parity << 3) | air
    reg1 = (subpacket << 6) | (rssi_ambient << 5) | power
    reg2 = channel
    reg3 = (rssi_byte << 7) | (fixed_tx << 6) | (lbt << 4) | wor

    return bytes([
        0xC0, 0x00, 0x07,
        (addr >> 8) & 0xFF, addr & 0xFF, netid,
        reg0, reg1, reg2, reg3,
    ])


def freq_mhz(channel: int) -> float:
    return 850.125 + channel


def apply(port: str, baud: int, settings: dict):
    """설정 프레임을 모듈에 기록. 설정 모드 진입은 M0/M1 핀 제어가 필요하다.

    settings["gpio"] = {"m0": <pin>, "m1": <pin>} 를 주면 GPIO 로 자동 전환을 시도한다.
    (OPi.GPIO 또는 gpiod 필요) 없으면 수동으로 M0=1,M1=1 로 두고 실행하라고 안내한다.
    설정 모드 UART 는 항상 9600 8N1.
    """
    import serial
    frame = build_config_frame(settings)
    ch = int(settings.get("channel", 70))
    logger.info(f"E22 설정: 채널 {ch} ({freq_mhz(ch):.3f}MHz), 주소 {settings.get('address', 0)}, "
                f"NETID {settings.get('netid', 0)}, 프레임={frame.hex()}")

    gpio = settings.get("gpio")
    restore = _enter_config_mode(gpio)
    try:
        with serial.Serial(port, baudrate=9600, timeout=1.0) as ser:  # 설정 모드는 9600 고정
            ser.write(frame)
            ser.flush()
            time.sleep(0.2)
            resp = ser.read(64)
            logger.info(f"E22 응답: {resp.hex()}")
            if resp[:1] == b"\xc1":
                logger.info("E22 설정 성공(C1 응답)")
            else:
                logger.warning("E22 설정 응답이 C1 이 아님 — 설정 모드(M0=1,M1=1) 확인 필요")
    finally:
        if restore:
            restore()


def _enter_config_mode(gpio):
    """M0=1,M1=1 로 설정 모드 진입. 복귀 콜백 반환(없으면 None)."""
    if not gpio:
        logger.warning("GPIO 미지정: 모듈을 수동으로 설정 모드(M0=1, M1=1)에 두고 실행하세요. "
                       "완료 후 M0=0, M1=0(전송 모드)로 복귀.")
        return None
    try:
        import OPi.GPIO as GPIO  # Orange Pi
    except Exception:
        try:
            import RPi.GPIO as GPIO  # 호환 보드
        except Exception:
            logger.warning("GPIO 라이브러리 없음 — 수동으로 M0=1,M1=1 설정 후 진행하세요.")
            return None

    m0, m1 = int(gpio["m0"]), int(gpio["m1"])
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(m0, GPIO.OUT); GPIO.setup(m1, GPIO.OUT)
    GPIO.output(m0, GPIO.HIGH); GPIO.output(m1, GPIO.HIGH)  # 설정 모드
    time.sleep(0.1)

    def restore():
        GPIO.output(m0, GPIO.LOW); GPIO.output(m1, GPIO.LOW)  # 전송 모드
        time.sleep(0.1)
        GPIO.cleanup([m0, m1])
        logger.info("E22 전송 모드(M0=0,M1=0) 복귀")

    return restore


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser(description="E22 LoRa 모듈 설정")
    p.add_argument("--port", default="/dev/ttyS0")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--channel", type=int, default=70)
    p.add_argument("--address", type=int, default=0)
    p.add_argument("--netid", type=int, default=0)
    p.add_argument("--air-rate", type=int, default=9600)
    p.add_argument("--power-dbm", type=int, default=30)
    args = p.parse_args()
    apply(args.port, args.baud, {
        "channel": args.channel, "address": args.address, "netid": args.netid,
        "air_rate": args.air_rate, "power_dbm": args.power_dbm,
    })


if __name__ == "__main__":
    main()
