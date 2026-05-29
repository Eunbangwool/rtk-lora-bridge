package com.rtklorabridge

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import androidx.core.app.NotificationCompat
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

        startForeground(NOTIF_ID, buildNotification("시작 중..."))
        caster.start(scope)

        if (lora.connect()) {
            lora.startReading(scope) { data ->
                caster.broadcast(data)
            }
            // 상태 모니터링
            scope.launch {
                lora.bytesPerSec.collect { bps ->
                    updateNotification(
                        if (bps > 0) "수신 중 • ${bps} bytes/s • 클라이언트 ${caster.clientCount.value}대"
                        else "대기 중..."
                    )
                }
            }
        } else {
            updateNotification("LoRa 수신기 연결 안됨 - USB를 확인하세요")
        }

        return START_STICKY
    }

    override fun onDestroy() {
        lora.disconnect()
        caster.stop()
        scope.cancel()
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
