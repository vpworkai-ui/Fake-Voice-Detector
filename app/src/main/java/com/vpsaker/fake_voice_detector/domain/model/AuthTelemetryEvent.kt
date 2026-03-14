package com.vpsaker.fake_voice_detector.domain.model

data class AuthTelemetryEvent(
    val timestampMs: Long,
    val spoofProbability: Float,
    val asvScore: Float,
    val decision: String,
    val reason: String,
    val asvSource: String,
    val asvLatencyMs: Long,
    val modelName: String,
    val recordingDurationSec: Float
)
