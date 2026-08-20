package com.rtklorabridge

import kotlinx.coroutines.flow.MutableStateFlow

/**
 * 서비스(RtkService)와 UI(RtkViewModel/Compose)가 공유하는 상태 홀더.
 *
 * RtkService 는 자신의 UsbLoRaManager/NtripCaster 를 실제로 구동하고,
 * 그 상태를 이 싱글턴에 반영한다. UI 는 이 싱글턴을 관찰한다.
 * (예전에는 ViewModel 이 별도의 미구동 인스턴스를 봐서 화면이 실제 상태를 반영하지 못했음)
 */
object RtkState {
    val serviceRunning = MutableStateFlow(false)
    val isConnected = MutableStateFlow(false)
    val bytesPerSec = MutableStateFlow(0)
    val clientCount = MutableStateFlow(0)

    /** 현재 lock 된 RTCM 기준국 ID (없으면 null). */
    val stationId = MutableStateFlow<Int?>(null)

    /** 다른 기지국 신호로 폐기된 프레임 수. */
    val droppedOtherStation = MutableStateFlow(0)

    /** CRC 불일치(손상/충돌)로 폐기된 프레임 수. */
    val droppedCrc = MutableStateFlow(0)

    /** 서비스 종료 시 상태 초기화. */
    fun onServiceStopped() {
        serviceRunning.value = false
        isConnected.value = false
        bytesPerSec.value = 0
        clientCount.value = 0
        stationId.value = null
    }
}
