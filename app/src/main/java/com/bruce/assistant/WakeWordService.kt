package com.bruce.assistant

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.PowerManager
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import androidx.core.app.NotificationCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import org.vosk.Model
import org.vosk.Recognizer
import org.vosk.android.RecognitionListener
import org.vosk.android.SpeechService
import org.vosk.android.StorageService
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.TimeUnit

class WakeWordService : Service(), RecognitionListener {
    private var speech: SpeechService? = null
    private var model: Model? = null
    private var tts: TextToSpeech? = null
    private var wakeLock: PowerManager.WakeLock? = null
    private var awaitingCommand = false
    private var commandHandled = false
    private var lastWakeAt = 0L
    private val mainHandler = Handler(Looper.getMainLooper())
    private val http = OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS)
        .readTimeout(180, TimeUnit.SECONDS).callTimeout(190, TimeUnit.SECONDS).build()

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    override fun onCreate() {
        super.onCreate()
        createChannel()
        startForeground(NOTIFICATION_ID, notification("Preparando reconhecimento offline"))
        val power = getSystemService(PowerManager::class.java)
        wakeLock = power.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "BRUCE:WakeWord").also { it.acquire() }
        tts = TextToSpeech(this) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale("pt", "BR")
                tts?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
                    override fun onStart(id: String?) {}
                    override fun onDone(id: String?) {
                        if (id == "bruce-prompt") mainHandler.post { startCommandRecognition() }
                        if (id == "bruce-answer") mainHandler.post { startWakeRecognition() }
                    }
                    @Deprecated("Deprecated in Java")
                    override fun onError(id: String?) { mainHandler.post { startWakeRecognition() } }
                    override fun onError(id: String?, errorCode: Int) { mainHandler.post { startWakeRecognition() } }
                })
            }
        }
        StorageService.unpack(this, "model-pt", "model-pt",
            { loaded -> model = loaded; startWakeRecognition() },
            { error -> updateNotification("Falha ao preparar voz: ${error.message}") }
        )
    }

    private fun startWakeRecognition() {
        awaitingCommand = false
        commandHandled = false
        stopSpeech()
        try {
            val recognizer = Recognizer(model, SAMPLE_RATE, "[\"bruce\"]")
            speech = SpeechService(recognizer, SAMPLE_RATE)
            speech?.startListening(this)
            updateNotification("Ativo. Diga BRUCE para chamar.")
        } catch (e: Exception) {
            updateNotification("Não foi possível ouvir: ${e.message}")
        }
    }

    private fun startCommandRecognition() {
        awaitingCommand = true
        commandHandled = false
        stopSpeech()
        try {
            val recognizer = Recognizer(model, SAMPLE_RATE)
            speech = SpeechService(recognizer, SAMPLE_RATE)
            speech?.startListening(this)
            updateNotification("BRUCE está ouvindo seu pedido.")
        } catch (e: Exception) {
            speakAndReturn("Tive um problema para ouvir você. Tente me chamar novamente.")
        }
    }

    override fun onPartialResult(hypothesis: String?) {
        if (!awaitingCommand && containsBruce(hypothesis)) onWakeWord()
    }

    override fun onResult(hypothesis: String?) {
        val text = extractText(hypothesis)
        if (!awaitingCommand && text.contains("bruce")) onWakeWord()
        else if (awaitingCommand && text.isNotBlank()) handleCommand(text)
    }

    override fun onFinalResult(hypothesis: String?) {
        val text = extractText(hypothesis)
        if (!awaitingCommand && text.contains("bruce")) onWakeWord()
        else if (awaitingCommand && text.isNotBlank()) handleCommand(text)
    }

    override fun onError(exception: Exception) {
        if (awaitingCommand) speakAndReturn("Não consegui entender. Pode me chamar novamente.")
        else {
            updateNotification("Reconectando ao microfone.")
            mainHandler.postDelayed({ startWakeRecognition() }, 1200)
        }
    }

    override fun onTimeout() {
        if (awaitingCommand && !commandHandled) speakAndReturn("Não ouvi seu pedido. Quando precisar, diga BRUCE.")
        else if (!awaitingCommand) mainHandler.post { startWakeRecognition() }
    }

    private fun onWakeWord() {
        val now = System.currentTimeMillis()
        if (awaitingCommand || now - lastWakeAt < 4000) return
        lastWakeAt = now
        awaitingCommand = true
        commandHandled = false
        stopSpeech()
        tts?.speak("Estou aqui. Pode falar.", TextToSpeech.QUEUE_FLUSH, null, "bruce-prompt")
        updateNotification("BRUCE foi chamado. Pode falar.")
    }

    private fun handleCommand(command: String) {
        if (commandHandled) return
        if (System.currentTimeMillis() - lastWakeAt < 1800 && command.trim().equals("bruce", ignoreCase = true)) return
        commandHandled = true
        val prefs = BruceSecurePrefs.get(this)
        val baseUrl = prefs.getString(BruceSecurePrefs.API_URL, "").orEmpty().trim().trimEnd('/')
        val token = prefs.getString(BruceSecurePrefs.API_TOKEN, "").orEmpty().trim()
        if (baseUrl.isBlank() || token.isBlank()) {
            speakAndReturn(localFallback(command))
            return
        }
        awaitingCommand = false
        stopSpeech()
        updateNotification("Consultando a inteligência própria do BRUCE.")
        Thread {
            try {
                val payload = JSONObject()
                    .put("conversation_id", prefs.getString(BruceSecurePrefs.CONVERSATION_ID, JSONObject.NULL))
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", command)))
                val body = payload.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url("$baseUrl/v1/chat")
                    .header("Authorization", "Bearer $token")
                    .post(body).build()
                http.newCall(request).execute().use { response ->
                    val raw = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw IllegalStateException("API retornou HTTP ${response.code}")
                    val result = JSONObject(raw)
                    val answer = result.optString("message").takeIf { it.isNotBlank() }
                        ?: throw IllegalStateException("A API retornou uma resposta vazia.")
                    val id = result.optString("conversation_id")
                    if (id.isNotBlank()) prefs.edit().putString(BruceSecurePrefs.CONVERSATION_ID, id).apply()
                    mainHandler.post { speakAndReturn(answer) }
                }
            } catch (error: Exception) {
                mainHandler.post {
                    speakAndReturn("Não consegui acessar a inteligência do BRUCE. Verifique a conexão com sua API. Detalhe: ${error.message ?: "erro de rede"}.")
                }
            }
        }.start()
    }

    private fun localFallback(command: String): String {
        val normalized = command.lowercase(Locale("pt", "BR"))
        return when {
            normalized.contains("que horas") || normalized.contains("horário") ->
                "Agora são " + SimpleDateFormat("HH:mm", Locale("pt", "BR")).format(Date()) + "."
            normalized.contains("que dia") || normalized.contains("data de hoje") ->
                "Hoje é " + SimpleDateFormat("EEEE, d 'de' MMMM", Locale("pt", "BR")).format(Date()) + "."
            normalized.contains("seu nome") || normalized.contains("quem é você") ->
                "Eu sou BRUCE, seu assistente pessoal. Configure a API própria para ativar minha inteligência conversacional."
            else ->
                "Ouvi você dizer: $command. Para responder com inteligência conversacional, configure a URL HTTPS e o token da API BRUCE no aplicativo."
        }
    }

    private fun speakAndReturn(message: String) {
        awaitingCommand = false
        stopSpeech()
        tts?.speak(message, TextToSpeech.QUEUE_FLUSH, null, "bruce-answer")
            ?: mainHandler.postDelayed({ startWakeRecognition() }, 1500)
    }

    private fun containsBruce(raw: String?): Boolean = extractText(raw).contains("bruce")

    private fun extractText(raw: String?): String {
        if (raw.isNullOrBlank()) return ""
        return try {
            val json = JSONObject(raw)
            (json.optString("text") + " " + json.optString("partial")).trim().lowercase(Locale.ROOT)
        } catch (_: Exception) {
            raw.lowercase(Locale.ROOT)
        }
    }

    private fun stopSpeech() {
        try { speech?.stop() } catch (_: Exception) {}
        try { speech?.shutdown() } catch (_: Exception) {}
        speech = null
    }

    private fun createChannel() {
        getSystemService(NotificationManager::class.java).createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "BRUCE - Ativação por voz", NotificationManager.IMPORTANCE_LOW)
        )
    }

    private fun notification(message: String): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentTitle("BRUCE")
            .setContentText(message)
            .setContentIntent(open)
            .addAction(android.R.drawable.ic_media_pause, "Desativar", PendingIntent.getService(this, 2, Intent(this, WakeWordService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE))
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(message: String) {
        getSystemService(NotificationManager::class.java).notify(NOTIFICATION_ID, notification(message))
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        stopSpeech()
        model?.close()
        tts?.shutdown()
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    companion object {
        private const val CHANNEL_ID = "bruce_voice"
        private const val NOTIFICATION_ID = 41
        private const val SAMPLE_RATE = 16000.0f
        private const val ACTION_STOP = "com.bruce.assistant.STOP"
    }
}
