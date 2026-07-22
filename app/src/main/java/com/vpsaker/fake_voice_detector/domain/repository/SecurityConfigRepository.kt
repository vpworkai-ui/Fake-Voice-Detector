package com.vpsaker.fake_voice_detector.domain.repository

import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import kotlinx.coroutines.flow.Flow

interface SecurityConfigRepository {
    val configFlow: Flow<SecurityConfig>
    suspend fun updateSpoofThreshold(value: Float)
}
