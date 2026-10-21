plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

val releaseStore = System.getenv("DSBCA_ANDROID_KEYSTORE")
val releasePassword = System.getenv("DSBCA_ANDROID_STORE_PASSWORD")
val releaseAlias = System.getenv("DSBCA_ANDROID_KEY_ALIAS")
val releaseKeyPassword = System.getenv("DSBCA_ANDROID_KEY_PASSWORD")
val releaseConfigured = listOf(releaseStore, releasePassword, releaseAlias, releaseKeyPassword).all { !it.isNullOrBlank() }
if (gradle.startParameter.taskNames.any { it.contains("Release", ignoreCase = true) } && !releaseConfigured) {
    throw GradleException("Release signing is not configured. Supply the four DSBCA_ANDROID signing environment variables; debug signing is never used for release.")
}

android {
    namespace = "com.dsbca.dsbca_user"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // TODO: Specify your own unique Application ID (https://developer.android.com/studio/build/application-id.html).
        applicationId = "com.dsbca.dsbca_user"
        // You can update the following values to match your application needs.
        // For more information, see: https://flutter.dev/to/review-gradle-config.
        minSdk = 24
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    signingConfigs {
        if (releaseConfigured) {
            create("production") {
                storeFile = file(releaseStore!!)
                storePassword = releasePassword
                keyAlias = releaseAlias
                keyPassword = releaseKeyPassword
            }
        }
    }
    buildTypes {
        release {
            if (releaseConfigured) signingConfig = signingConfigs.getByName("production")
            isMinifyEnabled = true
            isShrinkResources = true
        }
    }
}

flutter {
    source = "../.."
}
