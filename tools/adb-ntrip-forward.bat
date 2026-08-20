@echo off
REM ============================================================
REM  태블릿의 NtripCaster(:2101)를 PC의 127.0.0.1:2101 로 노출
REM  (USB + ADB). farmmachine-auto-steering / AgIO 의 NTRIP
REM  클라이언트가 caster 주소를 127.0.0.1:2101 로 접속하면 된다.
REM
REM  사용:
REM    1) 태블릿 USB 디버깅 ON, PC에 USB 연결
REM    2) 이 파일 실행 (adb 가 PATH 에 있어야 함; 없으면 ADB_PATH 수정)
REM    3) AgIO NTRIP: IP=127.0.0.1, Port=2101, Mount=RTCM32, user/pw 공란
REM ============================================================

set PORT=2101
set ADB_PATH=adb

echo [1/3] 연결된 기기 확인...
%ADB_PATH% devices
if errorlevel 1 (
  echo adb 를 찾을 수 없습니다. ADB_PATH 를 platform-tools 의 adb.exe 경로로 수정하세요.
  pause
  exit /b 1
)

echo [2/3] 기존 포워딩 제거...
%ADB_PATH% forward --remove tcp:%PORT% 2>nul

echo [3/3] 포워딩 설정: PC 127.0.0.1:%PORT%  ->  태블릿 :%PORT%
%ADB_PATH% forward tcp:%PORT% tcp:%PORT%
if errorlevel 1 (
  echo 포워딩 실패. 기기 인증/USB 디버깅 상태를 확인하세요.
  pause
  exit /b 1
)

echo.
echo 완료. 현재 포워딩 목록:
%ADB_PATH% forward --list
echo.
echo 이제 auto-steering / AgIO 에서 NTRIP caster 를 127.0.0.1:%PORT% 로 설정하세요.
pause
