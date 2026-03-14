package com.vpsaker.fake_voice_detector.domain.model

data class DetectionSession(
    val createdAtEpochMs: Long,
    val detectionResult: DetectionResult,
    val fusionDecision: FusionDecisionResult
)
