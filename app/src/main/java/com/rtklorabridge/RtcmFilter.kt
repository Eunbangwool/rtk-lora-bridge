package com.rtklorabridge

import kotlinx.coroutines.flow.MutableStateFlow

/**
 * RTCM3 스트림 안전 필터.
 *
 * 여러 LoRa 기지국 신호가 겹치는 구역에서 발생하는 두 문제를 막는다.
 *  1) RF 충돌로 손상된 프레임  → CRC-24Q 검증으로 폐기
 *  2) 서로 다른 기준국 혼합     → 하나의 Reference Station ID 에만 lock, 나머지 폐기
 *
 * 바이트 스트림을 누적하며 완전하고 CRC 가 유효한 프레임만 골라,
 * lock 된 기준국에 해당하는 프레임을 onFrame 으로 전달한다.
 *
 * 단일 기지국 환경에서도 안전하게 동작한다(첫 기준국에 lock, 손상 프레임 제거).
 */
class RtcmFilter {

    private var pending = ByteArray(0)

    /** 현재 lock 된 기준국 ID (아직 없으면 null). */
    val lockedStationId = MutableStateFlow<Int?>(null)

    /** lock 된 기준국과 달라서 버린 프레임 수 (다른 기지국 신호 유입 진단용). */
    val droppedOtherStation = MutableStateFlow(0)

    /** CRC 불일치로 버린(손상/충돌) 프레임 수. */
    val droppedCrc = MutableStateFlow(0)

    fun reset() {
        pending = ByteArray(0)
        lockedStationId.value = null
        droppedOtherStation.value = 0
        droppedCrc.value = 0
    }

    /**
     * 새 바이트를 누적 파싱한다. 청크 경계에 걸친 프레임도 다음 호출에서 이어 처리한다.
     * 유효하고 lock 기준국에 해당하는 완전한 프레임마다 onFrame 을 호출한다.
     */
    fun push(data: ByteArray, onFrame: (ByteArray) -> Unit) {
        pending = if (pending.isEmpty()) data.copyOf() else pending + data
        val n = pending.size
        var pos = 0

        while (true) {
            // 0xD3 preamble 탐색
            var start = pos
            while (start < n && (pending[start].toInt() and 0xFF) != 0xD3) start++
            if (start >= n) { pos = n; break }          // preamble 없음 → 전부 소진
            if (n - start < 3) { pos = start; break }    // 헤더 부족 → 다음 청크 대기

            // 상위 6비트는 reserved, 하위 10비트가 메시지 길이
            val len = ((pending[start + 1].toInt() and 0x03) shl 8) or
                    (pending[start + 2].toInt() and 0xFF)
            val frameLen = 3 + len + 3                   // 헤더(3) + 페이로드(len) + CRC(3)
            if (n - start < frameLen) { pos = start; break } // 프레임 미완성 → 대기

            if (crc24q(pending, start, 3 + len) == readU24(pending, start + 3 + len)) {
                if (acceptByStation(pending, start, len)) {
                    onFrame(pending.copyOfRange(start, start + frameLen))
                }
                pos = start + frameLen
            } else {
                droppedCrc.value = droppedCrc.value + 1
                pos = start + 1                          // 손상 프레임 → 1바이트 건너뛰고 재동기화
            }
        }

        pending = if (pos >= pending.size) ByteArray(0) else pending.copyOfRange(pos, pending.size)
    }

    /** 기준국 lock 적용. 전달 대상이면 true. */
    private fun acceptByStation(buf: ByteArray, start: Int, len: Int): Boolean {
        if (len < 3) return true
        val p0 = buf[start + 3].toInt() and 0xFF
        val p1 = buf[start + 4].toInt() and 0xFF
        val msgType = (p0 shl 4) or (p1 shr 4)
        if (!hasStationId(msgType)) return true          // 기준국 ID 없는 타입 → 통과

        val p2 = buf[start + 5].toInt() and 0xFF
        val stationId = ((p1 and 0x0F) shl 8) or p2      // DF003: 12비트

        val locked = lockedStationId.value
        if (locked == null) {
            lockedStationId.value = stationId            // 처음 잡힌 기준국에 lock
            return true
        }
        if (stationId == locked) return true
        droppedOtherStation.value = droppedOtherStation.value + 1
        return false                                     // 다른 기지국 → 폐기
    }

    /** DF002(메시지번호) 바로 뒤에 DF003(기준국 ID)이 오는 메시지 타입인가. */
    private fun hasStationId(msgType: Int): Boolean =
        msgType in 1001..1013 || msgType == 1033 || msgType == 1230 || msgType in 1071..1127

    private fun readU24(buf: ByteArray, off: Int): Int =
        ((buf[off].toInt() and 0xFF) shl 16) or
        ((buf[off + 1].toInt() and 0xFF) shl 8) or
        (buf[off + 2].toInt() and 0xFF)

    /** RTCM CRC-24Q (poly 0x1864CFB, init 0). */
    private fun crc24q(buf: ByteArray, off: Int, length: Int): Int {
        var crc = 0
        for (i in 0 until length) {
            crc = crc xor ((buf[off + i].toInt() and 0xFF) shl 16)
            for (b in 0 until 8) {
                crc = crc shl 1
                if (crc and 0x1000000 != 0) crc = crc xor 0x1864CFB
            }
        }
        return crc and 0xFFFFFF
    }
}
