package com.bruce.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONArray
import org.json.JSONObject
import java.util.concurrent.TimeUnit

private data class BruceMessage(val role: String, val content: String)

class MainActivity : ComponentActivity() {
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result -> if (result[Manifest.permission.RECORD_AUDIO] == true) startBruceService() }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = BruceSecurePrefs.get(this)
        setContent {
            var apiUrl by remember { mutableStateOf(prefs.getString(BruceSecurePrefs.API_URL, "") ?: "") }
            var apiToken by remember { mutableStateOf(prefs.getString(BruceSecurePrefs.API_TOKEN, "") ?: "") }
            var draftUrl by remember { mutableStateOf(apiUrl) }
            var draftToken by remember { mutableStateOf(apiToken) }
            var showSettings by remember { mutableStateOf(apiUrl.isBlank() || apiToken.isBlank()) }
            var input by remember { mutableStateOf("") }
            var status by remember { mutableStateOf("SUA INTELIGÊNCIA PRIVADA") }
            var busy by remember { mutableStateOf(false) }
            var conversationId by remember { mutableStateOf(prefs.getString(BruceSecurePrefs.CONVERSATION_ID, null)) }
            val messages = remember { mutableStateListOf(BruceMessage("assistant", "Estou aqui. Sou BRUCE, seu assistente pessoal. Configure sua API privada para ativar a inteligência conversacional.")) }
            val listState = rememberLazyListState()
            val client = remember { OkHttpClient.Builder().connectTimeout(20, TimeUnit.SECONDS).readTimeout(180, TimeUnit.SECONDS).build() }
            val handler = remember { Handler(Looper.getMainLooper()) }

            LaunchedEffect(messages.size) {
                if (messages.isNotEmpty()) listState.animateScrollToItem(messages.lastIndex)
            }

            MaterialTheme(colorScheme = darkColorScheme(
                primary = Color(0xFFB7E1FF), onPrimary = Color(0xFF07131E),
                background = Color(0xFF080A0D), surface = Color(0xFF11151B),
                onSurface = Color(0xFFE8EDF3), secondary = Color(0xFF85BCE8)
            )) {
                Surface(Modifier.fillMaxSize(), color = Color(0xFF080A0D)) {
                    Column(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF101720), Color(0xFF080A0D))))) {
                        Row(
                            Modifier.fillMaxWidth().height(62.dp).padding(horizontal = 18.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Box(Modifier.size(34.dp).background(Color(0xFF172738), RoundedCornerShape(10.dp)), contentAlignment = Alignment.Center) {
                                Text("◉", color = Color(0xFFB7E1FF), fontSize = 20.sp)
                            }
                            Column(Modifier.padding(start = 10.dp).weight(1f)) {
                                Text("BRUCE", color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold, letterSpacing = 3.sp)
                                Text(status, color = Color(0xFF8296AA), fontSize = 8.sp, letterSpacing = 1.sp)
                            }
                            TextButton(onClick = { showSettings = !showSettings }) { Text("CONFIG", color = Color(0xFF9BB9D3), fontSize = 10.sp) }
                            TextButton(onClick = {
                                conversationId = null
                                prefs.edit().remove(BruceSecurePrefs.CONVERSATION_ID).apply()
                                messages.clear()
                                messages.add(BruceMessage("assistant", "Nova conversa. O que vamos resolver?"))
                            }) { Text("＋", color = Color(0xFFB7E1FF), fontSize = 22.sp) }
                        }
                        if (showSettings) {
                            Column(
                                Modifier.fillMaxWidth().padding(horizontal = 15.dp, vertical = 8.dp)
                                    .background(Color(0xFF111923), RoundedCornerShape(14.dp)).padding(14.dp)
                            ) {
                                Text("CONECTAR INTELIGÊNCIA PRÓPRIA", color = Color(0xFFE4F1FC), fontSize = 11.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.sp)
                                Text("A chave do modelo fica no servidor. Aqui use apenas a URL da API e o token privado do BRUCE.", color = Color(0xFF8192A4), fontSize = 10.sp, lineHeight = 15.sp, modifier = Modifier.padding(top = 6.dp, bottom = 10.dp))
                                OutlinedTextField(value = draftUrl, onValueChange = { draftUrl = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("URL HTTPS da API") })
                                Spacer(Modifier.height(8.dp))
                                OutlinedTextField(value = draftToken, onValueChange = { draftToken = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("Token privado do dispositivo") }, visualTransformation = PasswordVisualTransformation())
                                Button(
                                    onClick = {
                                        apiUrl = draftUrl.trim().trimEnd('/')
                                        apiToken = draftToken.trim()
                                        prefs.edit().putString(BruceSecurePrefs.API_URL, apiUrl).putString(BruceSecurePrefs.API_TOKEN, apiToken).apply()
                                        showSettings = false
                                        status = "CONEXÃO SALVA"
                                    },
                                    modifier = Modifier.fillMaxWidth().padding(top = 9.dp)
                                ) { Text("SALVAR CONEXÃO") }
                            }
                        }
                        Column(Modifier.weight(1f).fillMaxWidth()) {
                            if (messages.size == 1 && messages[0].role == "assistant") {
                                val orbitTransition = rememberInfiniteTransition(label = "bruce-neural-core")
                                val orbitRotation by orbitTransition.animateFloat(
                                    initialValue = 0f, targetValue = 360f,
                                    animationSpec = infiniteRepeatable(tween(18000, easing = LinearEasing)),
                                    label = "orbit-rotation"
                                )
                                Column(Modifier.fillMaxWidth().weight(1f), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                                    Canvas(Modifier.size(250.dp)) {
                                        val centerPoint = Offset(size.width / 2f, size.height / 2f)
                                        rotate(orbitRotation) {
                                            drawOval(
                                                color = Color(0x668CCBFA),
                                                topLeft = Offset(size.width * 0.04f, size.height * 0.32f),
                                                size = Size(size.width * 0.92f, size.height * 0.36f),
                                                style = Stroke(width = 1.3.dp.toPx())
                                            )
                                        }
                                        rotate(-orbitRotation * 0.72f) {
                                            drawOval(
                                                color = Color(0x557DBBE8),
                                                topLeft = Offset(size.width * 0.29f, size.height * 0.04f),
                                                size = Size(size.width * 0.42f, size.height * 0.92f),
                                                style = Stroke(width = 1.1.dp.toPx())
                                            )
                                        }
                                        rotate(orbitRotation * 0.43f) {
                                            drawOval(
                                                color = Color(0x447CB8E4),
                                                topLeft = Offset(size.width * 0.13f, size.height * 0.16f),
                                                size = Size(size.width * 0.74f, size.height * 0.68f),
                                                style = Stroke(width = 1.dp.toPx())
                                            )
                                        }
                                        drawCircle(
                                            brush = Brush.radialGradient(
                                                colors = listOf(Color(0xFFBFE9FF), Color(0xFF4A91C5), Color(0xFF10263B), Color(0xFF05090F)),
                                                center = centerPoint,
                                                radius = size.minDimension * 0.29f
                                            ),
                                            radius = size.minDimension * 0.22f,
                                            center = centerPoint
                                        )
                                        drawCircle(
                                            color = Color(0xFFB4E4FF),
                                            radius = size.minDimension * 0.22f,
                                            center = centerPoint,
                                            style = Stroke(width = 1.4.dp.toPx())
                                        )
                                    }
                                    Text("PROTOCOLO", color = Color(0xFF91B6D2), fontSize = 9.sp, letterSpacing = 5.sp, modifier = Modifier.padding(top = 1.dp))
                                    Text("BRUCE WAYNE", color = Color(0xFFEAF2F8), fontSize = 25.sp, fontWeight = FontWeight.Light, letterSpacing = 4.sp, modifier = Modifier.padding(top = 8.dp))
                                    Text("INTELIGÊNCIA PESSOAL · SISTEMA AUTÔNOMO", color = Color(0xFF8291A1), fontSize = 8.sp, letterSpacing = 1.2.sp, modifier = Modifier.padding(top = 8.dp))
                                    Button(onClick = { activateVoice() }, modifier = Modifier.padding(top = 20.dp)) { Text("ATIVAR BRUCE · VOZ OFFLINE") }
                                }
                            } else {
                                LazyColumn(
                                    state = listState,
                                    modifier = Modifier.weight(1f).fillMaxWidth().padding(horizontal = 16.dp),
                                    contentPadding = PaddingValues(vertical = 20.dp),
                                    verticalArrangement = Arrangement.spacedBy(18.dp)
                                ) {
                                    items(messages) { message ->
                                        Column(Modifier.fillMaxWidth()) {
                                            Text(if (message.role == "assistant") "BRUCE" else "VOCÊ", color = Color(0xFF8FAFCB), fontSize = 9.sp, letterSpacing = 1.5.sp)
                                            Text(message.content, color = Color(0xFFD9E0E8), fontSize = 13.sp, lineHeight = 21.sp, modifier = Modifier.padding(top = 6.dp))
                                        }
                                    }
                                    if (busy) item { Text("BRUCE ESTÁ PENSANDO…", color = Color(0xFF8FAFCB), fontSize = 10.sp) }
                                }
                            }
                        }
                        Row(
                            Modifier.fillMaxWidth().padding(horizontal = 13.dp, vertical = 9.dp)
                                .background(Color(0xFF121821), RoundedCornerShape(15.dp)).padding(start = 14.dp, end = 7.dp, top = 5.dp, bottom = 5.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            BasicTextField(
                                value = input, onValueChange = { input = it },
                                modifier = Modifier.weight(1f).padding(vertical = 12.dp),
                                textStyle = androidx.compose.ui.text.TextStyle(color = Color.White, fontSize = 13.sp),
                                decorationBox = { inner -> if (input.isEmpty()) Text("Mensagem para BRUCE…", color = Color(0xFF697888), fontSize = 13.sp); inner() }
                            )
                            TextButton(onClick = { activateVoice() }) { Text("🎙", fontSize = 18.sp) }
                            Button(
                                onClick = {
                                    val question = input.trim()
                                    if (question.isNotEmpty() && !busy) {
                                        input = ""
                                        messages.add(BruceMessage("user", question))
                                        if (apiUrl.isBlank() || apiToken.isBlank()) {
                                            messages.add(BruceMessage("assistant", "Configure a URL e o token privado da sua API nas configurações."))
                                        } else {
                                            busy = true; status = "PROCESSANDO"
                                            Thread {
                                                try {
                                                    val body = JSONObject()
                                                        .put("conversation_id", conversationId)
                                                        .put("messages", JSONArray().put(JSONObject().put("role", "user").put("content", question)))
                                                        .toString().toRequestBody("application/json".toMediaType())
                                                    val request = Request.Builder().url("$apiUrl/v1/chat")
                                                        .header("Authorization", "Bearer $apiToken").post(body).build()
                                                    client.newCall(request).execute().use { response ->
                                                        val raw = response.body?.string().orEmpty()
                                                        if (!response.isSuccessful) throw IllegalStateException("API HTTP ${response.code}")
                                                        val result = JSONObject(raw)
                                                        val answer = result.optString("message")
                                                        val id = result.optString("conversation_id")
                                                        handler.post {
                                                            if (id.isNotBlank()) {
                                                                conversationId = id
                                                                prefs.edit().putString(BruceSecurePrefs.CONVERSATION_ID, id).apply()
                                                            }
                                                            messages.add(BruceMessage("assistant", answer))
                                                            busy = false; status = "NÚCLEO CONECTADO"
                                                        }
                                                    }
                                                } catch (e: Exception) {
                                                    handler.post {
                                                        messages.add(BruceMessage("assistant", "Não consegui acessar a API: ${e.message}"))
                                                        busy = false; status = "FALHA DE CONEXÃO"
                                                    }
                                                }
                                            }.start()
                                        }
                                    }
                                },
                                enabled = input.isNotBlank() && !busy,
                                shape = RoundedCornerShape(11.dp),
                                contentPadding = PaddingValues(horizontal = 15.dp, vertical = 9.dp)
                            ) { Text("↑", fontSize = 19.sp) }
                        }
                        Row(Modifier.fillMaxWidth().padding(horizontal = 18.dp, vertical = 5.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("BRUCE · IA INDEPENDENTE", color = Color(0xFF566575), fontSize = 8.sp, letterSpacing = 1.sp)
                            Text("VOZ + MEMÓRIA", color = Color(0xFF566575), fontSize = 8.sp, letterSpacing = 1.sp)
                        }
                    }
                }
            }
        }
    }

    private fun activateVoice() {
        val needed = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) needed.add(Manifest.permission.POST_NOTIFICATIONS)
        val missing = needed.filter { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }
        if (missing.isEmpty()) startBruceService() else permissionLauncher.launch(missing.toTypedArray())
    }

    private fun startBruceService() {
        val intent = Intent(this, WakeWordService::class.java)
        ContextCompat.startForegroundService(this, intent)
    }
}
