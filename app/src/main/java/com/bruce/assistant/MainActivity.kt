package com.bruce.assistant

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.*
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private val permissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { result ->
        if (result[Manifest.permission.RECORD_AUDIO] == true) startBruceService()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val prefs = BruceSecurePrefs.get(this)
        setContent {
            var apiUrl by remember { mutableStateOf(prefs.getString(BruceSecurePrefs.API_URL, "") ?: "") }
            var apiToken by remember { mutableStateOf(prefs.getString(BruceSecurePrefs.API_TOKEN, "") ?: "") }
            var status by remember { mutableStateOf("PRONTO PARA CONFIGURAR") }
            MaterialTheme {
                BruceHome(
                    apiUrl = apiUrl,
                    apiToken = apiToken,
                    status = status,
                    onApiUrlChange = { apiUrl = it },
                    onApiTokenChange = { apiToken = it },
                    onSave = {
                        prefs.edit()
                            .putString(BruceSecurePrefs.API_URL, apiUrl.trim().trimEnd('/'))
                            .putString(BruceSecurePrefs.API_TOKEN, apiToken.trim())
                            .apply()
                        status = "CONEXÃO SALVA COM SEGURANÇA"
                    },
                    onActivate = {
                        val needed = mutableListOf(Manifest.permission.RECORD_AUDIO)
                        if (Build.VERSION.SDK_INT >= 33) needed += Manifest.permission.POST_NOTIFICATIONS
                        val missing = needed.filter {
                            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
                        }
                        if (missing.isEmpty()) {
                            startBruceService()
                            status = "BRUCE ESTÁ AGUARDANDO A PALAVRA-CHAVE"
                        } else permissionLauncher.launch(missing.toTypedArray())
                    }
                )
            }
        }
    }

    private fun startBruceService() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
            ContextCompat.startForegroundService(this, Intent(this, WakeWordService::class.java))
        }
    }
}

@Composable
private fun BruceHome(
    apiUrl: String,
    apiToken: String,
    status: String,
    onApiUrlChange: (String) -> Unit,
    onApiTokenChange: (String) -> Unit,
    onSave: () -> Unit,
    onActivate: () -> Unit
) {
    val infinite = rememberInfiniteTransition(label = "core")
    val pulse by infinite.animateFloat(.82f, 1.08f, infiniteRepeatable(tween(1900, easing = EaseInOutSine), RepeatMode.Reverse), label = "pulse")
    val rotation by infinite.animateFloat(0f, 360f, infiniteRepeatable(tween(18000, easing = LinearEasing)), label = "rotation")
    Surface(Modifier.fillMaxSize(), color = Color(0xFF07090D)) {
        Column(
            Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF111923), Color(0xFF050608))))
                .verticalScroll(rememberScrollState()).padding(horizontal = 24.dp, vertical = 30.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Spacer(Modifier.height(12.dp))
            Text("B R U C E", color = Color(0xFFF2F5FA), fontSize = 25.sp, fontWeight = FontWeight.Light, letterSpacing = 8.sp)
            Spacer(Modifier.height(28.dp))
            Box(Modifier.size(240.dp), contentAlignment = Alignment.Center) {
                Canvas(Modifier.fillMaxSize()) {
                    val c = center
                    val radius = size.minDimension * .31f * pulse
                    drawCircle(Brush.radialGradient(listOf(Color(0x553FBAFF), Color(0x223B8DFF), Color.Transparent), c, radius * 1.8f), radius * 1.8f)
                    drawCircle(Color(0x663CAEFF), radius * 1.32f, style = Stroke(1.2.dp.toPx()))
                    drawCircle(Color(0xAA75D4FF), radius, style = Stroke(2.dp.toPx()))
                    drawCircle(Color(0xFFB8E9FF), radius * .72f)
                    for (i in 0..11) {
                        val a = Math.toRadians((i * 30.0 + rotation).toDouble())
                        val p1 = androidx.compose.ui.geometry.Offset(c.x + kotlin.math.cos(a).toFloat() * radius * 1.08f, c.y + kotlin.math.sin(a).toFloat() * radius * 1.08f)
                        val p2 = androidx.compose.ui.geometry.Offset(c.x + kotlin.math.cos(a).toFloat() * radius * 1.22f, c.y + kotlin.math.sin(a).toFloat() * radius * 1.22f)
                        drawLine(Color(0xFF7CCEFF), p1, p2, 2.dp.toPx())
                    }
                }
                Box(Modifier.size(92.dp).blur(22.dp).background(Color(0x664ABEFF), CircleShape))
                Box(Modifier.size(56.dp).background(Brush.radialGradient(listOf(Color.White, Color(0xFF69C8FF), Color(0xFF1468B5))), CircleShape))
            }
            Spacer(Modifier.height(20.dp))
            Text("SEU ASSISTENTE PESSOAL", color = Color(0xFFDDEAF5), fontSize = 12.sp, letterSpacing = 2.sp)
            Text("Diga BRUCE para chamar", color = Color(0xFF8B9AAA), fontSize = 14.sp, modifier = Modifier.padding(top = 9.dp))
            Button(onClick = onActivate, modifier = Modifier.padding(top = 20.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173B59))) {
                Text("ATIVAR BRUCE")
            }
            Text(status, color = Color(0xFF9EB9D8), fontSize = 10.sp, letterSpacing = 1.2.sp, modifier = Modifier.padding(top = 12.dp))
            Spacer(Modifier.height(28.dp))
            Column(Modifier.fillMaxWidth().background(Color(0xFF101722), MaterialTheme.shapes.large).padding(18.dp)) {
                Text("INTELIGÊNCIA PRÓPRIA", color = Color(0xFFE6F2FC), fontSize = 13.sp, fontWeight = FontWeight.SemiBold, letterSpacing = 1.2.sp)
                Text("Conecte a API do BRUCE. A chave do modelo fica no servidor, nunca neste aplicativo.", color = Color(0xFF8797A8), fontSize = 11.sp, lineHeight = 17.sp, modifier = Modifier.padding(top = 7.dp, bottom = 14.dp))
                OutlinedTextField(
                    value = apiUrl, onValueChange = onApiUrlChange,
                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                    label = { Text("URL HTTPS da API BRUCE") },
                    placeholder = { Text("https://api.seudominio.com") },
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White, unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF78BDEB), unfocusedBorderColor = Color(0xFF465363),
                        focusedLabelColor = Color(0xFF9CCEF0), unfocusedLabelColor = Color(0xFF8998A8)
                    )
                )
                Spacer(Modifier.height(10.dp))
                OutlinedTextField(
                    value = apiToken, onValueChange = onApiTokenChange,
                    modifier = Modifier.fillMaxWidth(), singleLine = true,
                    label = { Text("Token privado do dispositivo") },
                    visualTransformation = PasswordVisualTransformation(),
                    colors = OutlinedTextFieldDefaults.colors(
                        focusedTextColor = Color.White, unfocusedTextColor = Color.White,
                        focusedBorderColor = Color(0xFF78BDEB), unfocusedBorderColor = Color(0xFF465363),
                        focusedLabelColor = Color(0xFF9CCEF0), unfocusedLabelColor = Color(0xFF8998A8)
                    )
                )
                Button(onClick = onSave, modifier = Modifier.fillMaxWidth().padding(top = 14.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF263D53))) {
                    Text("SALVAR CONEXÃO")
                }
            }
            Spacer(Modifier.height(22.dp))
            Text("BRUCE • VOZ LOCAL • API INDEPENDENTE", color = Color(0xFF647586), fontSize = 9.sp, letterSpacing = 1.1.sp)
        }
    }
}
