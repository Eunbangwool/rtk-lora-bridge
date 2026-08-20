"""RTCM3 프레임 처리 공유 코어 (기지국 브리지용).

프레임 구조:
    [0]      0xD3 preamble
    [1..2]   상위 6비트 reserved + 하위 10비트 메시지 길이(len)
    [3..]    페이로드(len 바이트)  — 앞 12비트 = 메시지번호(DF002),
             station-id 계열 메시지는 이어서 12비트 = 기준국 ID(DF003)
    [3+len..] CRC-24Q 3바이트

안드로이드 수신기(RtcmFilter.kt)와 동일한 파싱/CRC 규약을 쓴다.
"""

# DF002(메시지번호) 바로 뒤에 DF003(기준국 ID)이 오는 메시지 타입
def has_station_id(msg_type: int) -> bool:
    return 1001 <= msg_type <= 1013 or msg_type == 1033 or msg_type == 1230 or 1071 <= msg_type <= 1127


def crc24q(buf, off: int, length: int) -> int:
    """RTCM CRC-24Q (poly 0x1864CFB, init 0)."""
    crc = 0
    for i in range(length):
        crc ^= (buf[off + i] & 0xFF) << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= 0x1864CFB
    return crc & 0xFFFFFF


def message_type(frame) -> int:
    p0 = frame[3] & 0xFF
    p1 = frame[4] & 0xFF
    return (p0 << 4) | (p1 >> 4)


def station_id(frame):
    """기준국 ID 반환. 해당 없는 타입이면 None."""
    if message_type(frame) and not has_station_id(message_type(frame)):
        return None
    p1 = frame[4] & 0xFF
    p2 = frame[5] & 0xFF
    return ((p1 & 0x0F) << 8) | p2


def set_station_id(frame: bytearray, sid: int) -> bytearray:
    """프레임의 DF003(기준국 ID)을 sid 로 덮어쓰고 CRC 를 재계산한다.

    기준국 ID 없는 타입이면 CRC 만 유지한 채 그대로 반환.
    frame 은 [헤더3 + 페이로드 + CRC3] 완전 프레임(bytearray).
    """
    length = ((frame[1] & 0x03) << 8) | (frame[2] & 0xFF)
    if has_station_id(message_type(frame)):
        frame[4] = (frame[4] & 0xF0) | ((sid >> 8) & 0x0F)
        frame[5] = sid & 0xFF
        crc = crc24q(frame, 0, 3 + length)
        frame[3 + length] = (crc >> 16) & 0xFF
        frame[3 + length + 1] = (crc >> 8) & 0xFF
        frame[3 + length + 2] = crc & 0xFF
    return frame


class RtcmReader:
    """바이트 스트림을 누적하며 완전하고 CRC 가 유효한 RTCM3 프레임을 뽑아낸다."""

    MAX_PAYLOAD = 1023

    def __init__(self):
        self._buf = bytearray()
        self.crc_errors = 0

    def push(self, data) -> list:
        """새 바이트 누적 후, 추출된 프레임(bytes) 리스트 반환."""
        self._buf.extend(data)
        b = self._buf
        n = len(b)
        pos = 0
        frames = []
        while True:
            # preamble 탐색
            start = pos
            while start < n and b[start] != 0xD3:
                start += 1
            if start >= n:
                pos = n
                break
            if n - start < 3:
                pos = start
                break
            length = ((b[start + 1] & 0x03) << 8) | b[start + 2]
            frame_len = 3 + length + 3
            if n - start < frame_len:
                pos = start
                break
            crc_calc = crc24q(b, start, 3 + length)
            crc_frame = (b[start + 3 + length] << 16) | (b[start + 3 + length + 1] << 8) | b[start + 3 + length + 2]
            if crc_calc == crc_frame:
                frames.append(bytes(b[start:start + frame_len]))
                pos = start + frame_len
            else:
                self.crc_errors += 1
                pos = start + 1  # 손상 → 1바이트 건너뛰고 재동기화
        del self._buf[:pos]
        return frames
