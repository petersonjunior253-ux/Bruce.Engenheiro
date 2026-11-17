package ai.bruce.assistant

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.EditText
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.core.content.ContextCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.Locale
import java.util.concurrent.TimeUnit

class MainActivity : Activity() {
    private lateinit var status: TextView
    private lateinit var transcript: TextView
    private lateinit var apiUrl: EditText
    private lateinit var apiToken: EditText
    private lateinit var wakeKey: EditText
    private val client = OkHttpClient.Builder().callTimeout(120, TimeUnit.SECONDS).build()
    private val prefs by lazy { getSharedPreferences("bruce", MODE_PRIVATE) }
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val granted = results[Manifest.permission.RECORD_AUDIO] == true
        if (granted) startWakeService() else status.text = "Permissão de microfone negada"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        buildScreen()
        if (intent?.action == ACTION_WAKE) startSpeechCapture()
    }

    private fun buildScreen() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(36, 52, 36, 36)
            setBackgroundColor(0xFF08090C.toInt())
        }
        fun label(value: String, size: Float = 16f) = TextView(this).apply {
            text = value
            textSize = size
            setTextColor(0xFFE9F1F8.toInt())
            setPadding(0, 12, 0, 12)
        }
        status = label("BRUCE • Assistente pessoal", 22f)
        transcript = label("Ative o monitoramento para detectar BRUCE localmente.")
        apiUrl = EditText(this).apply {
            hint = "URL da API BRUCE (ex.: https://seu-servidor)"
            setSingleLine(true)
            setText(prefs.getString("api_url", ""))
            setTextColor(0xFFFFFFFF.toInt())
            setHintTextColor(0xFF8493A5.toInt())
        }
        apiToken = EditText(this).apply {
            hint = "Token de acesso BRUCE"
            setSingleLine(true)
            setText(prefs.getString("api_token", ""))
            setTextColor(0xFFFFFFFF.toInt())
            setHintTextColor(0xFF8493A5.toInt())
        }
        wakeKey = EditText(this).apply {
            hint = "Picovoice Access Key (detector BRUCE)"
            setSingleLine(true)
            setText(prefs.getString("picovoice_access_key", ""))
            setTextColor(0xFFFFFFFF.toInt())
            setHintTextColor(0xFF8493A5.toInt())
        }
        val save = Button(this).apply {
            text = "Salvar conexão segura"
            setOnClickListener {
                prefs.edit().putString("api_url", apiUrl.text.toString().trim().trimEnd('/'))
                    .putString("api_token", apiToken.text.toString().trim())
                    .putString("picovoice_access_key", wakeKey.text.toString().trim()).apply()
                Toast.makeText(this@MainActivity, "Configuração salva neste aparelho", Toast.LENGTH_SHORT).show()
            }
        }
        val start = Button(this).apply {
            text = "Ativar palavra BRUCE"
            setOnClickListener { requestMicAndStart() }
        }
        val stop = Button(this).apply {
            text = "Desativar microfone"
            setOnClickListener {
                stopService(Intent(this@MainActivity, WakeWordService::class.java))
                status.text = "Monitoramento desligado"
            }
        }
        root.addView(status)
        root.addView(label("O detector da palavra-chave funciona localmente. O áudio só é processado após a ativação."))
        root.addView(apiUrl)
        root.addView(apiToken)
        root.addView(wakeKey)
        root.addView(save)
        root.addView(start)
        root.addView(stop)
        root.addView(transcript)
        setContentView(root)
    }

    private fun requestMicAndStart() {
        val permissions = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) permissions.add(Manifest.permission.POST_NOTIFICATIONS)
        val missing = permissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) startWakeService()
        else permissionLauncher.launch(missing.toTypedArray())
    }

    private fun startWakeService() {
        val intent = Intent(this, WakeWordService::class.java)
        ContextCompat.startForegroundService(this, intent)
        status.text = "BRUCE aguardando a palavra de ativação"
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        if (intent?.action == ACTION_WAKE) startSpeechCapture()
    }

    private fun startSpeechCapture() {
        if (!SpeechRecognizer.isRecognitionAvailable(this)) {
            transcript.text = "Reconhecimento de fala indisponível neste aparelho."
            return
        }
        val recognizer = SpeechRecognizer.createSpeechRecognizer(this)
        recognizer.setRecognitionListener(object : android.speech.RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) { runOnUiThread { status.text = "Pode falar…" } }
            override fun onBeginningOfSpeech() {}
            override fun onRmsChanged(rmsdB: Float) {}
            override fun onBufferReceived(buffer: ByteArray?) {}
            override fun onEndOfSpeech() {}
            override fun onError(error: Int) { runOnUiThread { status.text = "Não foi possível reconhecer a fala (código $error)." }; recognizer.destroy() }
            override fun onResults(results: Bundle?) {
                val text = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)?.firstOrNull().orEmpty()
                runOnUiThread { transcript.text = "Você: $text" }
                if (text.isNotBlank()) sendToBruce(text)
                recognizer.destroy()
            }
            override fun onPartialResults(partialResults: Bundle?) {}
            override fun onEvent(eventType: Int, params: Bundle?) {}
        })
        val request = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL, RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, "pt-BR")
            putExtra(RecognizerIntent.EXTRA_PROMPT, "Fale com BRUCE")
        }
        recognizer.startListening(request)
    }

    private fun sendToBruce(text: String) {
        val base = prefs.getString("api_url", "").orEmpty()
        val token = prefs.getString("api_token", "").orEmpty()
        if (base.isBlank() || token.isBlank()) {
            transcript.text = "Comando reconhecido: $text\nConfigure a URL e o token da API BRUCE."
            return
        }
        Thread {
            try {
                val payload = JSONObject()
                    .put("conversation_id", prefs.getString("conversation_id", JSONObject.NULL))
                    .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", text)))
                val body = payload.toString().toRequestBody("application/json".toMediaType())
                val request = Request.Builder().url("$base/v1/chat")
                    .header("Authorization", "Bearer $token").post(body).build()
                client.newCall(request).execute().use { response ->
                    val result = response.body?.string().orEmpty()
                    if (!response.isSuccessful) throw IllegalStateException("API HTTP ${response.code}: $result")
                    val parsed = JSONObject(result)
                    val answer = parsed.optString("message", "Resposta vazia")
                    prefs.edit().putString("conversation_id", parsed.optString("conversation_id")).apply()
                    runOnUiThread {
                        transcript.text = "BRUCE: $answer"
                        val tts = android.speech.tts.TextToSpeech(this) { code ->
                            if (code == android.speech.tts.TextToSpeech.SUCCESS) {
                                ttsEngine?.language = Locale("pt", "BR")
                                ttsEngine?.speak(answer, android.speech.tts.TextToSpeech.QUEUE_FLUSH, null, "bruce-answer")
                            }
                        }
                        ttsEngine = tts
                    }
                }
            } catch (error: Exception) {
                runOnUiThread { transcript.text = "Falha na conexão: ${error.message}" }
            }
        }.start()
    }

    private var ttsEngine: android.speech.tts.TextToSpeech? = null

    override fun onDestroy() {
        ttsEngine?.shutdown()
        super.onDestroy()
    }

    companion object {
        const val ACTION_WAKE = "ai.bruce.assistant.WAKE"
    }
}
