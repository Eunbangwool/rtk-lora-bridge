package com.rtklorabridge

import android.app.Application
import android.content.Intent
import androidx.core.content.ContextCompat
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

class RtkViewModel(app: Application) : AndroidViewModel(app) {

    private val lora = UsbLoRaManager(app)
    private val caster = NtripCaster(2101)

    val isConnected: StateFlow<Boolean> = lora.isConnected
    val bytesPerSec: StateFlow<Int> = lora.bytesPerSec
    val clientCount: StateFlow<Int> = caster.clientCount

    private val _serviceRunning = MutableStateFlow(false)
    val serviceRunning: StateFlow<Boolean> = _serviceRunning

    fun startService() {
        val intent = Intent(getApplication(), RtkService::class.java)
        ContextCompat.startForegroundService(getApplication(), intent)
        _serviceRunning.value = true
    }

    fun stopService() {
        val intent = Intent(getApplication(), RtkService::class.java).apply {
            action = RtkService.ACTION_STOP
        }
        getApplication<Application>().startService(intent)
        _serviceRunning.value = false
    }
}
