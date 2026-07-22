package com.vpsaker.fake_voice_detector.domain.model

enum class AuthenticationDecision {
    ALLOW,
    REVIEW,
    BLOCK
}

data class FusionDecisionResult(
    val decision: AuthenticationDecision,
    val reason: String,
    val spoofProbability: Float,
    val spoofThreshold: Float,
    val confidence: Float,
    val meetsSpoofThreshold: Boolean
)
