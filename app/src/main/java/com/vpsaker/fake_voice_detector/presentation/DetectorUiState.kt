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
    val spoofThreshold: Float = 0.25f,
    val lastTelemetryFlushCount: Int = 0,
    val telemetryStatus: String = "idle",
    val datasetLabel: String = "bonafide",
    val savedBonafideCount: Int = 0,
    val savedSpoofCount: Int = 0,
    val lastSavedSamplePath: String? = null,
    val isSavingSample: Boolean = false,
    val lastImportedFileName: String? = null,
    val sessions: List<DetectionSession> = emptyList(),
    val errorMessage: String? = null,
    // ── Hiệu năng thực tế ──────────────────────────────
    val lastTotalPipelineMs: Long = 0L,
    val lastInferenceMs: Long = 0L,
    val lastFeatureMs: Long = 0L,
    val lastRamMb: Float = 0f,
    // ── Xuất CSV ───────────────────────────────────────
    val lastExportPath: String? = null,
    val isExporting: Boolean = false
)
