package com.vpsaker.fake_voice_detector.domain.model

data class AsvScoreRequest(
    val endpoint: String,
    val spoofProbability: Float,
    val recordingDurationSec: Float,
    val sessionTimestampMs: Long
)

data class AsvScoreResult(
    val score: Float,
    val source: String,
    val latencyMs: Long
)
