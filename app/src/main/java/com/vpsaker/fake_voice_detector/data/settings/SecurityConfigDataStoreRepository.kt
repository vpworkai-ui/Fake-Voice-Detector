package com.vpsaker.fake_voice_detector.data.settings

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import com.vpsaker.fake_voice_detector.domain.repository.SecurityConfigRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private const val DATASTORE_NAME = "voice_security_config"
private val Context.securityDataStore by preferencesDataStore(name = DATASTORE_NAME)

class SecurityConfigDataStoreRepository(
    private val context: Context
) : SecurityConfigRepository {

    override val configFlow: Flow<SecurityConfig> = context.securityDataStore.data.map { preferences ->
        val rawThreshold = preferences[SPOOF_THRESHOLD_KEY]
        val configVersion = preferences[CONFIG_VERSION_KEY] ?: 0
        val normalizedThreshold = when {
            rawThreshold == null -> DEFAULT_SPOOF_THRESHOLD
            configVersion < CURRENT_CONFIG_VERSION -> DEFAULT_SPOOF_THRESHOLD
            else -> rawThreshold.coerceIn(MIN_THRESHOLD, MAX_THRESHOLD)
        }

        SecurityConfig(
            spoofThreshold = normalizedThreshold
        )
    }

    suspend fun ensureCurrentDefaults() {
        context.securityDataStore.edit { preferences ->
            val configVersion = preferences[CONFIG_VERSION_KEY] ?: 0
            if (configVersion < CURRENT_CONFIG_VERSION) {
                preferences[SPOOF_THRESHOLD_KEY] = DEFAULT_SPOOF_THRESHOLD
                preferences[CONFIG_VERSION_KEY] = CURRENT_CONFIG_VERSION
            } else if (preferences[SPOOF_THRESHOLD_KEY] == null) {
                preferences[SPOOF_THRESHOLD_KEY] = DEFAULT_SPOOF_THRESHOLD
            }
        }
    }

    override suspend fun updateSpoofThreshold(value: Float) {
        context.securityDataStore.edit { preferences ->
            preferences[SPOOF_THRESHOLD_KEY] = value.coerceIn(MIN_THRESHOLD, MAX_THRESHOLD)
            preferences[CONFIG_VERSION_KEY] = CURRENT_CONFIG_VERSION
        }
    }

    private companion object {
        val SPOOF_THRESHOLD_KEY = floatPreferencesKey("spoof_threshold")
        val CONFIG_VERSION_KEY = intPreferencesKey("config_version")

        const val CURRENT_CONFIG_VERSION = 1
        const val DEFAULT_SPOOF_THRESHOLD = 0.25f
        const val MIN_THRESHOLD = 0.05f
        const val MAX_THRESHOLD = 0.95f
    }
}
