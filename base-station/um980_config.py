#!/usr/bin/env python3
"""UM980 기지국 모드 설정 (Unicore 명령).

UM980 을 기지국으로 세워 RTCM3 를 출력하도록 명령을 보낸다.
두 가지 기준점 방식:
  - survey-in(자가측량): 일정 시간/정확도로 스스로 위치 확정  → MODE BASE TIME <sec> <hAcc> <vAcc>
  - fixed(고정좌표): 알고 있는 좌표 입력                       → MODE BASE <lat> <lon> <height>

명령은 Unicore/UM980 펌웨어 기준이며, 실제 펌웨어 버전에 맞는지 확인 권장.
config.json 의 "um980" 블록으로 오버라이드할 수 있다.

단독 실행:
    python3 um980_config.py --port /dev/ttyS1 --baud 115200
"""

import argparse
import logging
import time

logger = logging.getLogger("um980_config")

# LoRa 대역폭을 고려한 기본 RTCM 세트 (MSM4, 1초 주기) + 좌표/바이어스
DEFAULT_COMMANDS = [
    "UNLOG",                 # 기존 출력 정지
    "MODE BASE TIME 60 1.5 2.5",   # survey-in 60초, 수평 1.5m/수직 2.5m 수렴
    "RTCM1005 1",            # 기준국 좌표 (1초)
    "RTCM1074 1",            # GPS MSM4
    "RTCM1084 1",            # GLONASS MSM4
    "RTCM1094 1",            # Galileo MSM4
    "RTCM1124 1",            # BeiDou MSM4
    "RTCM1033 10",           # 안테나/수신기 기술자 (10초)
    "RTCM1230 10",           # GLONASS 코드-위상 바이어스 (10초)
    "SAVECONFIG",            # 재부팅해도 유지
]


def build_commands(um980_cfg: dict) -> list:
    """config 의 um980 블록으로 명령 목록 구성."""
    if um980_cfg.get("commands"):
        return list(um980_cfg["commands"])   # 완전 수동 오버라이드

    cmds = ["UNLOG"]

    mode = um980_cfg.get("mode", "survey")
    if mode == "fixed":
        lat = um980_cfg["lat"]; lon = um980_cfg["lon"]; height = um980_cfg["height"]
        cmds.append(f"MODE BASE {lat} {lon} {height}")
    else:  # survey-in
        sec = um980_cfg.get("survey_sec", 60)
        h = um980_cfg.get("survey_h_acc", 1.5)
        v = um980_cfg.get("survey_v_acc", 2.5)
        cmds.append(f"MODE BASE TIME {sec} {h} {v}")

    msgs = um980_cfg.get("rtcm_messages", {
        "RTCM1005": 1, "RTCM1074": 1, "RTCM1084": 1,
        "RTCM1094": 1, "RTCM1124": 1, "RTCM1033": 10, "RTCM1230": 10,
    })
    for name, interval in msgs.items():
        cmds.append(f"{name} {interval}")

    if um980_cfg.get("saveconfig", True):
        cmds.append("SAVECONFIG")
    return cmds


def apply(port: str, baud: int, um980_cfg: dict):
    import serial
    cmds = build_commands(um980_cfg)
    logger.info(f"UM980 설정 전송 → {port}@{baud}, {len(cmds)}개 명령")
    with serial.Serial(port, baudrate=baud, timeout=1.0) as ser:
        for c in cmds:
            ser.write((c + "\r\n").encode())
            ser.flush()
            time.sleep(0.2)
            resp = ser.read(256).decode("latin-1", "ignore").strip()
            logger.info(f"  > {c}  →  {resp!r}")
    logger.info("UM980 설정 완료")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    p = argparse.ArgumentParser(description="UM980 기지국 모드 설정")
    p.add_argument("--port", default="/dev/ttyS1")
    p.add_argument("--baud", type=int, default=115200)
    p.add_argument("--mode", choices=["survey", "fixed"], default="survey")
    p.add_argument("--lat", type=float)
    p.add_argument("--lon", type=float)
    p.add_argument("--height", type=float)
    args = p.parse_args()

    cfg = {"mode": args.mode}
    if args.mode == "fixed":
        cfg.update(lat=args.lat, lon=args.lon, height=args.height)
    apply(args.port, args.baud, cfg)


if __name__ == "__main__":
    main()
