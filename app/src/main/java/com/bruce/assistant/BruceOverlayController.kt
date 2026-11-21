package com.bruce.assistant

import android.animation.ObjectAnimator
import android.animation.ValueAnimator
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.Build
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.view.WindowManager
import android.view.animation.AccelerateDecelerateInterpolator
import android.widget.FrameLayout
import android.widget.TextView
import kotlin.math.roundToInt

/** Animated, non-focusable BRUCE orb shown over other apps while voice mode is active. */
class BruceOverlayController(private val context: Context) {
    private val windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager
    private var container: FrameLayout? = null
    private var pulseX: ObjectAnimator? = null
    private var pulseY: ObjectAnimator? = null

    fun show() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M || !Settings.canDrawOverlays(context)) return
        if (container != null) return

        val size = dp(68)
        val root = FrameLayout(context).apply {
            isClickable = true
            isFocusable = false
            setPadding(dp(5), dp(5), dp(5), dp(5))
            setOnClickListener {
                context.startActivity(
                    Intent(context, MainActivity::class.java)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_SINGLE_TOP)
                )
            }
        }
        val ring = View(context).apply {
            background = GradientDrawable().apply {
                shape = GradientDrawable.OVAL
                setColor(Color.TRANSPARENT)
                setStroke(dp(1), Color.argb(150, 137, 202, 246))
            }
        }
        root.addView(ring, FrameLayout.LayoutParams(-1, -1))

        val core = TextView(context).apply {
            text = "B"
            textSize = 23f
            setTextColor(Color.rgb(226, 245, 255))
            gravity = Gravity.CENTER
            background = GradientDrawable(
                GradientDrawable.Orientation.TL_BR,
                intArrayOf(Color.rgb(187, 229, 255), Color.rgb(62, 135, 190), Color.rgb(9, 28, 48))
            ).apply {
                shape = GradientDrawable.OVAL
                setStroke(dp(1), Color.argb(190, 177, 225, 255))
            }
            elevation = dp(8).toFloat()
        }
        root.addView(core, FrameLayout.LayoutParams(dp(48), dp(48), Gravity.CENTER))

        val params = WindowManager.LayoutParams(
            size,
            size,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.END
            x = dp(14)
            y = dp(170)
            alpha = 0.96f
        }
        try {
            windowManager.addView(root, params)
            container = root
            pulseX = ObjectAnimator.ofFloat(root, View.SCALE_X, 0.94f, 1.04f).apply {
                duration = 1700
                repeatMode = ValueAnimator.REVERSE
                repeatCount = ValueAnimator.INFINITE
                interpolator = AccelerateDecelerateInterpolator()
                start()
            }
            pulseY = ObjectAnimator.ofFloat(root, View.SCALE_Y, 0.94f, 1.04f).apply {
                duration = 1700
                repeatMode = ValueAnimator.REVERSE
                repeatCount = ValueAnimator.INFINITE
                interpolator = AccelerateDecelerateInterpolator()
                start()
            }
        } catch (_: Exception) {
            container = null
        }
    }

    fun remove() {
        pulseX?.cancel()
        pulseY?.cancel()
        pulseX = null
        pulseY = null
        container?.let { view -> try { windowManager.removeView(view) } catch (_: Exception) { } }
        container = null
    }

    private fun dp(value: Int): Int = (value * context.resources.displayMetrics.density).roundToInt()
}
