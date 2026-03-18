plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
}

import org.jetbrains.kotlin.gradle.dsl.JvmTarget

fun resolveConfig(name: String, defaultValue: String): String {
    return (project.findProperty(name) as String?)?.trim()
        ?: System.getenv(name)?.trim()
        ?: defaultValue
}

fun quoteForBuildConfig(value: String): String {
    val escaped = value
        .replace("\\", "\\\\")
        .replace("\"", "\\\"")
    return "\"$escaped\""
}

android {
    namespace = "com.vpsaker.fake_voice_detector"
    compileSdk {
        version = release(36)
    }

    defaultConfig {
        applicationId = "com.vpsaker.fake_voice_detector"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        buildConfigField(
            "String",
            "ASV_ENDPOINT_DEFAULT",
            quoteForBuildConfig(resolveConfig("ASV_ENDPOINT", "https://example.com/api/asv/score"))
        )
        buildConfigField(
            "String",
            "TELEMETRY_ENDPOINT_DEFAULT",
            quoteForBuildConfig(resolveConfig("TELEMETRY_ENDPOINT", ""))
        )
        buildConfigField(
            "String",
            "ASV_API_KEY",
            quoteForBuildConfig(resolveConfig("ASV_API_KEY", ""))
        )
        buildConfigField(
            "String",
            "TELEMETRY_API_KEY",
            quoteForBuildConfig(resolveConfig("TELEMETRY_API_KEY", ""))
        )

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    androidResources {
        noCompress += "tflite"
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_11)
    }
}

dependencies {
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.runtime.compose)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.activity.compose)
    implementation(libs.androidx.datastore.preferences)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.google.litert)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.compose.ui)
    implementation(libs.androidx.compose.ui.graphics)
    implementation(libs.androidx.compose.ui.tooling.preview)
    implementation(libs.androidx.compose.material3)
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.compose.ui.test.junit4)
    debugImplementation(libs.androidx.compose.ui.tooling)
    debugImplementation(libs.androidx.compose.ui.test.manifest)
}
