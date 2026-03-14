package com.vpsaker.fake_voice_detector.domain.repository

import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent

interface TelemetryRepository {
    suspend fun logAuthenticationEvent(event: AuthTelemetryEvent): Result<Unit>
}
