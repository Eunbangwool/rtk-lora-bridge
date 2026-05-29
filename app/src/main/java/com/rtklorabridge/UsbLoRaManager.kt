package com.rtklorabridge

import android.content.Context
import android.hardware.usb.UsbManager
import com.hoho.android.usbserial.driver.UsbSerialProber
import com.hoho.android.usbserial.driver.UsbSerialPort
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow

class UsbLoRaManager(private val context: Context) {

    private var port: UsbSerialPort? = null
    private var readJob: Job? = null

    val isConnected = MutableStateFlow(false)
    val bytesPerSec = MutableStateFlow(0)

    fun connect(): Boolean {
        return try {
            val manager = context.getSystemService(Context.USB_SERVICE) as UsbManager
            val drivers = UsbSerialProber.getDefaultProber().findAllDrivers(manager)
            if (drivers.isEmpty()) return false

            val driver = drivers[0]
            val connection = manager.openDevice(driver.device) ?: return false

            port = driver.ports[0].also { p ->
                p.open(connection)
                p.setParameters(115200, 8, UsbSerialPort.STOPBITS_1, UsbSerialPort.PARITY_NONE)
                p.dtr = true
            }
            isConnected.value = true
            true
        } catch (e: Exception) {
            isConnected.value = false
            false
        }
    }

    fun startReading(scope: CoroutineScope, onData: (ByteArray) -> Unit) {
        readJob = scope.launch(Dispatchers.IO) {
            val buffer = ByteArray(1024)
            var byteCount = 0
            var lastSecond = System.currentTimeMillis()

            while (isActive) {
                try {
                    val len = port?.read(buffer, 100) ?: break
                    if (len > 0) {
                        onData(buffer.copyOf(len))
                        byteCount += len

                        val now = System.currentTimeMillis()
                        if (now - lastSecond >= 1000) {
                            bytesPerSec.value = byteCount
                            byteCount = 0
                            lastSecond = now
                        }
                    }
                } catch (e: Exception) {
                    isConnected.value = false
                    break
                }
            }
        }
    }

    fun disconnect() {
        readJob?.cancel()
        try { port?.close() } catch (e: Exception) {}
        port = null
        isConnected.value = false
        bytesPerSec.value = 0
    }
}
