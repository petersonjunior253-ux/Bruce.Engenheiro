import java.net.URL

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}
val voskModelAssets = layout.buildDirectory.dir("generated/voskAssets")
val downloadVoskModel by tasks.registering {
    val archiveFile = layout.buildDirectory.file("downloads/vosk-model-small-pt-0.3.zip")
    outputs.dir(voskModelAssets)
    doLast {
        val archive = archiveFile.get().asFile
        if (!archive.exists()) {
            archive.parentFile.mkdirs()
            URL("https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip").openStream().use { input ->
                archive.outputStream().use { output -> input.copyTo(output) }
            }
        }
        val root = voskModelAssets.get().asFile
        root.mkdirs()
        copy { from(zipTree(archive)); into(root) }
        val target = root.resolve("model-pt")
        if (target.exists()) target.deleteRecursively()
        val sourceModelRoot = root.walkTopDown().firstOrNull {
            it.isDirectory && it.resolve("am/final.mdl").isFile
        }
        check(sourceModelRoot != null) {
            "Modelo Vosk incompleto. Diretório am/final.mdl não encontrado. Conteúdo: " +
                root.walkTopDown().take(80).joinToString { it.relativeTo(root).path }
        }
        sourceModelRoot!!.copyRecursively(target, overwrite = true)
        check(target.resolve("am/final.mdl").isFile) { "Modelo Vosk incompleto após extração: am/final.mdl não encontrado." }
    }
}
android {
    namespace = "com.bruce.assistant"
    compileSdk = 35
    defaultConfig {
        applicationId = "com.bruce.assistant"
        minSdk = 26
        targetSdk = 34
        versionCode = 3
        versionName = "0.3.0"
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildFeatures { compose = true }
    packaging { resources.excludes += "/META-INF/{AL2.0,LGPL2.1}" }
    sourceSets.getByName("main").assets.srcDir(voskModelAssets)
}
tasks.named("preBuild").configure { dependsOn(downloadVoskModel) }
kotlin { jvmToolchain(17) }

dependencies {
    implementation(platform("androidx.compose:compose-bom:2024.12.01"))
    implementation("androidx.activity:activity-compose:1.10.0")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-graphics")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.security:security-crypto:1.1.0-alpha06")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")
    implementation("com.alphacephei:vosk-android:0.3.47")
    debugImplementation("androidx.compose.ui:ui-tooling")
}
