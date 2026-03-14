package com.vpsaker.fake_voice_detector.domain.repository

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult

interface VoiceSpoofingRepository {
    suspend fun startRecording(): Result<Unit>
    suspend fun stopRecordingAndAnalyze(): Result<DetectionResult>
    fun isRecording(): Boolean
}
