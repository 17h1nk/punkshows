plugins {
    id("com.android.application") version "8.6.0"
    id("org.jetbrains.kotlin.android") version "2.0.21"
    id("org.jetbrains.kotlin.plugin.compose") version "2.0.21"
}

kotlin {
    jvmToolchain(17)
}

dependencies {
    implementation("androidx.compose.material3:material3:1.4.0")
    implementation("androidx.compose.ui:ui:1.4.0")
}

android {
    namespace = "com.punkshows.app"
    compileSdk = 36

    buildFeatures {
        compose = true
    }

    defaultConfig {
        applicationId = "com.punkshows.app"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1"
    }
}
