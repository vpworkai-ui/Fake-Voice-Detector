package com.vpsaker.fake_voice_detector.domain.model

enum class AuthenticationDecision {
    ALLOW,
    REVIEW,
    BLOCK
}

data class FusionDecisionResult(
    val decision: AuthenticationDecision,
    val reason: String,
    val asvScore: Float,
    val spoofProbability: Float,
    val meetsAsvThreshold: Boolean,
    val meetsSpoofThreshold: Boolean
)
