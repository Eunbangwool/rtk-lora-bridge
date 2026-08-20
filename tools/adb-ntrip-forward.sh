#!/usr/bin/env bash
# ============================================================
#  태블릿의 NtripCaster(:2101)를 이 PC의 127.0.0.1:2101 로 노출 (USB + ADB).
#  farmmachine-auto-steering / AgIO 의 NTRIP 클라이언트가 127.0.0.1:2101 로 접속하면 된다.
#
#  사용:
#    1) 태블릿 USB 디버깅 ON, USB 연결
#    2) ./adb-ntrip-forward.sh
#    3) AgIO NTRIP: IP=127.0.0.1, Port=2101, Mount=RTCM32, user/pw 공란
# ============================================================
set -euo pipefail

PORT="${1:-2101}"
ADB="${ADB:-adb}"

echo "[1/3] 연결된 기기 확인..."
"$ADB" devices

echo "[2/3] 기존 포워딩 제거..."
"$ADB" forward --remove "tcp:${PORT}" 2>/dev/null || true

echo "[3/3] 포워딩 설정: PC 127.0.0.1:${PORT}  ->  태블릿 :${PORT}"
"$ADB" forward "tcp:${PORT}" "tcp:${PORT}"

echo
echo "완료. 현재 포워딩 목록:"
"$ADB" forward --list
echo
echo "이제 auto-steering / AgIO 에서 NTRIP caster 를 127.0.0.1:${PORT} 로 설정하세요."
