package com.bruce.assistant

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import org.json.JSONArray
import org.json.JSONObject

class BruceNotificationListener : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification?) { persistSnapshot() }
    override fun onNotificationRemoved(sbn: StatusBarNotification?) { persistSnapshot() }

    private fun persistSnapshot() {
        try {
            val items = JSONArray()
            for (entry in activeNotifications ?: emptyArray()) {
                val extras = entry.notification.extras
                val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
                val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
                if (title.isNotBlank() || text.isNotBlank()) {
                    items.put(JSONObject().put("app", entry.packageName).put("title", title).put("text", text).put("posted_at", entry.postTime))
                }
            }
            getSharedPreferences("bruce_notification_cache", MODE_PRIVATE).edit()
                .putString("active_notifications", items.toString()).apply()
        } catch (_: Exception) { }
    }
}
