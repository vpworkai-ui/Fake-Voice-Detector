package com.vpsaker.fake_voice_detector.presentation

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult

data class DetectorUiState(
    val isRecording: Boolean = false,
    val isAnalyzing: Boolean = false,
    val recordingSeconds: Int = 0,
    val result: DetectionResult? = null,
    val errorMessage: String? = null
)
