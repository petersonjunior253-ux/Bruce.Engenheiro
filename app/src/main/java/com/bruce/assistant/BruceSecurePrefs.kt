package com.bruce.assistant

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

object BruceSecurePrefs {
    const val API_URL = "api_url"
    const val API_TOKEN = "api_token"
    const val CONVERSATION_ID = "conversation_id"

    fun get(context: Context) = EncryptedSharedPreferences.create(
        context,
        "bruce_secure_settings",
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )
}
