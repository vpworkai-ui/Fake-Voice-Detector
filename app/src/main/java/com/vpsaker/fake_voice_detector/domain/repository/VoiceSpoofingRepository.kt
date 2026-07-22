package com.vpsaker.fake_voice_detector.domain.repository

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult

interface VoiceSpoofingRepository {
    suspend fun startRecording(): Result<Unit>
    suspend fun stopRecordingAndAnalyze(): Result<DetectionResult>
    suspend fun stopRecordingAndSaveSample(label: String): Result<String>
    suspend fun analyzeImportedAudio(fileName: String, data: ByteArray): Result<DetectionResult>
    fun isRecording(): Boolean
}
