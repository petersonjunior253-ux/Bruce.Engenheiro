package com.bruce.assistant

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import org.json.JSONArray

class BruceAccessibilityService : AccessibilityService() {
    companion object {
        @Volatile var instance: BruceAccessibilityService? = null
    }

    override fun onServiceConnected() { instance = this }
    override fun onAccessibilityEvent(event: AccessibilityEvent?) { }
    override fun onInterrupt() { }
    override fun onDestroy() {
        if (instance === this) instance = null
        super.onDestroy()
    }

    fun readScreenText(): String {
        val root = rootInActiveWindow ?: return ""
        val parts = JSONArray()
        collectText(root, parts, 0)
        val values = mutableListOf<String>()
        for (i in 0 until parts.length()) values.add(parts.optString(i))
        return values.distinct().joinToString("\n").take(16000)
    }

    private fun collectText(node: AccessibilityNodeInfo?, output: JSONArray, depth: Int) {
        if (node == null || depth > 30 || output.length() > 500) return
        val value = node.text?.toString()?.trim().orEmpty().ifBlank { node.contentDescription?.toString()?.trim().orEmpty() }
        if (value.isNotBlank()) output.put(value)
        for (i in 0 until node.childCount) collectText(node.getChild(i), output, depth + 1)
    }

    fun tapText(target: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = findNode(root) { n ->
            val text = n.text?.toString().orEmpty()
            val description = n.contentDescription?.toString().orEmpty()
            text.contains(target, true) || description.contains(target, true)
        } ?: return false
        var current: AccessibilityNodeInfo? = node
        while (current != null) {
            if (current.isClickable) return current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
            current = current.parent
        }
        return false
    }

    fun typeText(value: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT) ?: findNode(root) { it.isEditable } ?: return false
        val args = Bundle().apply { putCharSequence(AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, value) }
        return node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
    }

    fun scroll(direction: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val forward = direction != "up" && direction != "back"
        val node = findNode(root) { it.isScrollable } ?: return false
        return node.performAction(if (forward) AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD)
    }

    fun back(): Boolean = performGlobalAction(GLOBAL_ACTION_BACK)
    fun home(): Boolean = performGlobalAction(GLOBAL_ACTION_HOME)

    private fun findNode(node: AccessibilityNodeInfo?, depth: Int = 0, predicate: (AccessibilityNodeInfo) -> Boolean): AccessibilityNodeInfo? {
        if (node == null || depth > 30) return null
        if (predicate(node)) return node
        for (i in 0 until node.childCount) {
            val found = findNode(node.getChild(i), depth + 1, predicate)
            if (found != null) return found
        }
        return null
    }
}
