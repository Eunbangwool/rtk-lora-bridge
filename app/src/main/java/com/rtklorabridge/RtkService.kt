package com.rtklorabridge

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import kotlinx.coroutines.*

class RtkService : Service() {

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private lateinit var lora: UsbLoRaManager
    private lateinit var caster: NtripCaster

    companion object {
        const val CHANNEL_ID = "rtk_channel"
        const val NOTIF_ID = 1
        const val ACTION_STOP = "com.rtklorabridge.STOP"
    }

    override fun onCreate() {
        super.onCreate()
        lora = UsbLoRaManager(this)
        caster = NtripCaster(2101)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopSelf()
            return START_NOT_STICKY
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                ServiceCompat.startForeground(
                    this,
                    NOTIF_ID,
                    buildNotification("시작 중..."),
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE
                )
            } else {
                startForeground(NOTIF_ID, buildNotification("시작 중..."))
            }
        } catch (e: Exception) {
            Log.e("RtkService", "startForeground 실패", e)
            stopSelf()
            return START_NOT_STICKY
        }
        caster.start(scope)
        RtkState.serviceRunning.value = true
        publishState()

        if (lora.connect()) {
            lora.startReading(scope) { data ->
                caster.broadcast(data)
            }
            // 상태 모니터링 + 알림 갱신
            scope.launch {
                lora.bytesPerSec.collect { bps ->
                    val station = RtkState.stationId.value
                    val stationText = if (station != null) " • 기준국 $station" else ""
                    updateNotification(
                        if (bps > 0) "수신 중 • ${bps} bytes/s • 클라이언트 ${caster.clientCount.value}대$stationText"
                        else "대기 중..."
                    )
                }
            }
        } else {
            updateNotification("LoRa 수신기 연결 안됨 - USB를 확인하세요")
        }

        return START_STICKY
    }

    /** UsbLoRaManager/NtripCaster 의 상태 흐름을 공유 상태(RtkState)로 전달. */
    private fun publishState() {
        scope.launch { lora.isConnected.collect { RtkState.isConnected.value = it } }
        scope.launch { lora.bytesPerSec.collect { RtkState.bytesPerSec.value = it } }
        scope.launch { lora.lockedStationId.collect { RtkState.stationId.value = it } }
        scope.launch { lora.droppedOtherStation.collect { RtkState.droppedOtherStation.value = it } }
        scope.launch { lora.droppedCrc.collect { RtkState.droppedCrc.value = it } }
        scope.launch { caster.clientCount.collect { RtkState.clientCount.value = it } }
    }

    override fun onDestroy() {
        lora.disconnect()
        caster.stop()
        scope.cancel()
        RtkState.onServiceStopped()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "RTK LoRa Bridge",
            NotificationManager.IMPORTANCE_LOW
        )
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun buildNotification(message: String) =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("RTK LoRa Bridge")
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_menu_compass)
            .setOngoing(true)
            .build()

    private fun updateNotification(message: String) {
        val notif = buildNotification(message)
        getSystemService(NotificationManager::class.java).notify(NOTIF_ID, notif)
    }
}
