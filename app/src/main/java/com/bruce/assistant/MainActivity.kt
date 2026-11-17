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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.blur
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    private val permissionLauncher = registerForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { result ->
        if (result[Manifest.permission.RECORD_AUDIO] == true) startBruceService()
    }
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val needed = mutableListOf(Manifest.permission.RECORD_AUDIO)
        if (Build.VERSION.SDK_INT >= 33) needed += Manifest.permission.POST_NOTIFICATIONS
        if (needed.any { ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED }) permissionLauncher.launch(needed.toTypedArray())
        setContent { BruceHome(onActivate = { startBruceService() }) }
    }
    private fun startBruceService() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)
            ContextCompat.startForegroundService(this, Intent(this, WakeWordService::class.java))
    }
}

@Composable
private fun BruceHome(onActivate: () -> Unit) {
    val infinite = rememberInfiniteTransition(label = "core")
    val pulse by infinite.animateFloat(.82f, 1.08f, infiniteRepeatable(tween(1900, easing = EaseInOutSine), RepeatMode.Reverse), label = "pulse")
    val rotation by infinite.animateFloat(0f, 360f, infiniteRepeatable(tween(18000, easing = LinearEasing)), label = "rotation")
    Surface(Modifier.fillMaxSize(), color = Color(0xFF07090D)) {
        Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color(0xFF111923), Color(0xFF050608)))), contentAlignment = Alignment.Center) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                Text("B R U C E", color = Color(0xFFF2F5FA), fontSize = 25.sp, fontWeight = FontWeight.Light, letterSpacing = 8.sp)
                Spacer(Modifier.height(48.dp))
                Box(Modifier.size(270.dp), contentAlignment = Alignment.Center) {
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
                Spacer(Modifier.height(42.dp))
                Text("SEU ASSISTENTE PESSOAL", color = Color(0xFFDDEAF5), fontSize = 13.sp, letterSpacing = 2.sp)
                Spacer(Modifier.height(12.dp))
                Text("Diga BRUCE para chamar", color = Color(0xFF8B9AAA), fontSize = 14.sp)
                Spacer(Modifier.height(28.dp))
                Button(onClick = onActivate, colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF173B59))) { Text("ATIVAR BRUCE") }
                Spacer(Modifier.height(18.dp))
                Text("Ativação por voz • Português • Núcleo neural", color = Color(0xFF647586), fontSize = 11.sp)
            }
        }
    }
}
