package com.vpsaker.fake_voice_detector.data.detection

import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository

class VoiceSpoofingRepositoryImpl(
    private val recorder: AudioRecorder,
    private val featureExtractor: AudioFeatureExtractor,
    private val detectorEngine: SpoofDetectorEngine,
    private val sampleRateHz: Int = SAMPLE_RATE_HZ
) : VoiceSpoofingRepository {

    override suspend fun startRecording(): Result<Unit> {
        return recorder.start(sampleRateHz)
    }

    override suspend fun stopRecordingAndAnalyze(): Result<DetectionResult> {
        val audio = recorder.stop()
        if (audio.isEmpty()) {
            return Result.failure(IllegalStateException("No audio captured"))
        }

        return runCatching {
            val features = featureExtractor.extractFeatures(audio, sampleRateHz)
            val spoofProbability = detectorEngine.detectSpoofProbability(features)
            DetectionResult(
                spoofProbability = spoofProbability,
                modelName = detectorEngine.modelName,
                recordingDurationSec = audio.size.toFloat() / sampleRateHz.toFloat()
            )
        }
    }

    override fun isRecording(): Boolean = recorder.isRecording()

    companion object {
        const val SAMPLE_RATE_HZ = 16_000
    }
}
