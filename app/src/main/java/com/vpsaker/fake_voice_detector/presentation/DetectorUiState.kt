package com.vpsaker.fake_voice_detector.presentation

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult

data class DetectorUiState(
    val strictReleaseMode: Boolean = false,
    val isRecording: Boolean = false,
    val isAnalyzing: Boolean = false,
    val recordingSeconds: Int = 0,
    val result: DetectionResult? = null,
    val fusionDecisionResult: FusionDecisionResult? = null,
    val spoofThreshold: Float = 0.5f,
    val asvThreshold: Float = 0.75f,
    val useRemoteAsv: Boolean = false,
    val asvEndpoint: String = "https://example.com/api/asv/score",
    val asvScoreInput: String = "0.80",
    val lastAsvSource: String = "manual",
    val lastAsvLatencyMs: Long = 0L,
    val sessions: List<DetectionSession> = emptyList(),
    val errorMessage: String? = null
)
