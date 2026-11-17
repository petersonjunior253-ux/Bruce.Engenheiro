package com.bruce.assistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.speech.tts.TextToSpeech
import androidx.core.app.NotificationCompat
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService
import java.util.Locale

class WakeWordService : Service(), RecognitionListener {
    private var speech: SpeechService? = null
    private var model: Model? = null
    private var tts: TextToSpeech? = null
    private var triggeredAt = 0L
    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(41, notification("Preparando reconhecimento da palavra BRUCE"))
        tts = TextToSpeech(this) { status -> if (status == TextToSpeech.SUCCESS) tts?.language = Locale("pt", "BR") }
        StorageService.unpack(this, "model-pt", "model-pt",
            { loaded -> model = loaded; beginRecognition() },
            { error -> updateNotification("Falha ao carregar modelo de voz: ${error.message}") }
        )
    }
    private fun beginRecognition() {
        try {
            val recognizer = Recognizer(model, 16000.0f, "[\"bruce\"]")
            speech = SpeechService(recognizer, 16000.0f)
            speech?.startListening(this)
            updateNotification("Ouvindo a palavra BRUCE")
        } catch (e: Exception) { updateNotification("Falha no reconhecimento: ${e.message}") }
    }
    override fun onPartialResult(hypothesis: String?) = checkWakeWord(hypothesis)
    override fun onResult(hypothesis: String?) = checkWakeWord(hypothesis)
    override fun onFinalResult(hypothesis: String?) = checkWakeWord(hypothesis)
    override fun onError(exception: Exception) { updateNotification("Erro no microfone: ${exception.message}") }
    override fun onTimeout() { speech?.startListening(this) }
    private fun checkWakeWord(raw: String?) {
        if (raw.isNullOrBlank()) return
        val text = try { JSONObject(raw).optString("text") + " " + JSONObject(raw).optString("partial") } catch (_: Exception) { raw }
        if (text.lowercase(Locale.ROOT).contains("bruce") && System.currentTimeMillis() - triggeredAt > 5000) {
            triggeredAt = System.currentTimeMillis()
            tts?.speak("Estou aqui. Pode falar.", TextToSpeech.QUEUE_FLUSH, null, "bruce-wake")
            updateNotification("BRUCE foi chamado. Toque para abrir o assistente.")
            val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
            getSystemService(NotificationManager::class.java).notify(41,
                NotificationCompat.Builder(this, "bruce_voice").setSmallIcon(android.R.drawable.ic_btn_speak_now)
                    .setContentTitle("BRUCE está aqui").setContentText("Toque para abrir").setContentIntent(open).setAutoCancel(true).setOngoing(true).build())
        }
    }
    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) getSystemService(NotificationManager::class.java).createNotificationChannel(NotificationChannel("bruce_voice", "BRUCE - Voz", NotificationManager.IMPORTANCE_LOW))
    }
    private fun notification(message: String): Notification = NotificationCompat.Builder(this, "bruce_voice")
        .setSmallIcon(android.R.drawable.ic_btn_speak_now).setContentTitle("BRUCE").setContentText(message).setOngoing(true).build()
    private fun updateNotification(message: String) { getSystemService(NotificationManager::class.java).notify(41, notification(message)) }
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onDestroy() {
        speech?.stop(); speech = null; model?.close(); tts?.shutdown(); super.onDestroy()
    }
}
