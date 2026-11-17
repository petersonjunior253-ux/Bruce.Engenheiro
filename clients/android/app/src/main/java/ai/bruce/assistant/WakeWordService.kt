package ai.bruce.assistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import ai.picovoice.porcupine.Porcupine
import ai.picovoice.porcupine.PorcupineManager
import ai.picovoice.porcupine.PorcupineManagerCallback

class WakeWordService : Service() {
    private var manager: PorcupineManager? = null
    private val channelId = "bruce_wake_word"

    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(FOREGROUND_ID, notification())
        try {
            val prefs = getSharedPreferences("bruce", MODE_PRIVATE)
            val accessKey = prefs.getString("picovoice_access_key", "").orEmpty()
            if (accessKey.isBlank()) {
                stopSelf()
                return START_NOT_STICKY
            }
            manager = PorcupineManager.Builder()
                .setAccessKey(accessKey)
                .setKeywordPath("bruce_android.ppn")
                .setSensitivity(0.68f)
                .build(applicationContext, PorcupineManagerCallback {
                    val launch = Intent(this, MainActivity::class.java).apply {
                        action = MainActivity.ACTION_WAKE
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                    }
                    startActivity(launch)
                })
            manager?.start()
        } catch (error: Exception) {
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    override fun onDestroy() {
        try { manager?.stop() } catch (_: Exception) {}
        manager?.delete()
        manager = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(channelId, "BRUCE — ativação por voz", NotificationManager.IMPORTANCE_LOW)
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun notification(): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O)
            Notification.Builder(this, channelId) else Notification.Builder(this)
        return builder.setContentTitle("BRUCE está ativo")
            .setContentText("Detecção local da palavra de ativação. Toque para abrir.")
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(open)
            .setOngoing(true)
            .build()
    }

    companion object { private const val FOREGROUND_ID = 7301 }
}
