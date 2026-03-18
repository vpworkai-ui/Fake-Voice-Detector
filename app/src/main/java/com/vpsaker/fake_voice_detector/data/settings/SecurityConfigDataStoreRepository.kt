package com.vpsaker.fake_voice_detector.data.settings

import android.content.Context
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import com.vpsaker.fake_voice_detector.domain.repository.SecurityConfigRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

private const val DATASTORE_NAME = "voice_security_config"
private val Context.securityDataStore by preferencesDataStore(name = DATASTORE_NAME)

class SecurityConfigDataStoreRepository(
    private val context: Context,
    private val defaultUseRemoteAsv: Boolean = false,
    private val defaultAsvEndpoint: String = DEFAULT_ASV_ENDPOINT
) : SecurityConfigRepository {

    override val configFlow: Flow<SecurityConfig> = context.securityDataStore.data.map { preferences ->
        SecurityConfig(
            spoofThreshold = preferences[SPOOF_THRESHOLD_KEY] ?: DEFAULT_SPOOF_THRESHOLD,
            asvThreshold = preferences[ASV_THRESHOLD_KEY] ?: DEFAULT_ASV_THRESHOLD,
            useRemoteAsv = preferences[USE_REMOTE_ASV_KEY] ?: defaultUseRemoteAsv,
            asvEndpoint = preferences[ASV_ENDPOINT_KEY] ?: defaultAsvEndpoint
        )
    }

    override suspend fun updateSpoofThreshold(value: Float) {
        context.securityDataStore.edit { preferences ->
            preferences[SPOOF_THRESHOLD_KEY] = value.coerceIn(MIN_THRESHOLD, MAX_THRESHOLD)
        }
    }

    override suspend fun updateAsvThreshold(value: Float) {
        context.securityDataStore.edit { preferences ->
            preferences[ASV_THRESHOLD_KEY] = value.coerceIn(MIN_THRESHOLD, MAX_THRESHOLD)
        }
    }

    override suspend fun updateUseRemoteAsv(value: Boolean) {
        context.securityDataStore.edit { preferences ->
            preferences[USE_REMOTE_ASV_KEY] = value
        }
    }

    override suspend fun updateAsvEndpoint(value: String) {
        context.securityDataStore.edit { preferences ->
            preferences[ASV_ENDPOINT_KEY] = value.trim()
        }
    }

    private companion object {
        val SPOOF_THRESHOLD_KEY = floatPreferencesKey("spoof_threshold")
        val ASV_THRESHOLD_KEY = floatPreferencesKey("asv_threshold")
        val USE_REMOTE_ASV_KEY = booleanPreferencesKey("use_remote_asv")
        val ASV_ENDPOINT_KEY = stringPreferencesKey("asv_endpoint")

        const val DEFAULT_SPOOF_THRESHOLD = 0.5f
        const val DEFAULT_ASV_THRESHOLD = 0.75f
        const val DEFAULT_ASV_ENDPOINT = "https://example.com/api/asv/score"
        const val MIN_THRESHOLD = 0.05f
        const val MAX_THRESHOLD = 0.95f
    }
}
