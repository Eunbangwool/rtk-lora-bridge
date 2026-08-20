package com.rtklorabridge

import android.app.Application
import android.content.Intent
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import kotlinx.coroutines.flow.StateFlow

class RtkViewModel(app: Application) : AndroidViewModel(app) {

    // 실제 구동 중인 서비스(RtkService)의 상태를 공유 홀더(RtkState)에서 관찰
    val isConnected: StateFlow<Boolean> = RtkState.isConnected
    val bytesPerSec: StateFlow<Int> = RtkState.bytesPerSec
    val clientCount: StateFlow<Int> = RtkState.clientCount
    val serviceRunning: StateFlow<Boolean> = RtkState.serviceRunning
    val stationId: StateFlow<Int?> = RtkState.stationId
    val droppedOtherStation: StateFlow<Int> = RtkState.droppedOtherStation
    val droppedCrc: StateFlow<Int> = RtkState.droppedCrc

    fun startService() {
        val intent = Intent(getApplication(), RtkService::class.java)
        ContextCompat.startForegroundService(getApplication(), intent)
        RtkState.serviceRunning.value = true   // 즉시 반영(서비스가 곧 확정)
    }

    fun stopService() {
        val intent = Intent(getApplication(), RtkService::class.java).apply {
            action = RtkService.ACTION_STOP
        }
        getApplication<Application>().startService(intent)
        RtkState.serviceRunning.value = false
    }
}
