package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository

class AnalyzeVoiceSpoofingUseCase(
    private val repository: VoiceSpoofingRepository
) {
    suspend operator fun invoke(): Result<DetectionResult> {
        return repository.stopRecordingAndAnalyze()
    }
}
