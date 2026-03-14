package com.vpsaker.fake_voice_detector.domain.model

data class SecurityConfig(
    val spoofThreshold: Float = 0.5f,
    val asvThreshold: Float = 0.75f,
    val useRemoteAsv: Boolean = false,
    val asvEndpoint: String = "https://example.com/api/asv/score"
)
