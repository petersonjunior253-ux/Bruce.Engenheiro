plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "ai.bruce.assistant"
    compileSdk = 35

    defaultConfig {
        applicationId = "ai.bruce.assistant"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.activity:activity-ktx:1.9.3")
    implementation("ai.picovoice:porcupine-android:3.0.3")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
}
