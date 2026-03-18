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
            validateAudioQuality(features)
            val spoofProbability = detectorEngine.detectSpoofProbability(features)
            DetectionResult(
                spoofProbability = spoofProbability,
                modelName = detectorEngine.modelName,
                recordingDurationSec = audio.size.toFloat() / sampleRateHz.toFloat()
            )
        }
    }

    override fun isRecording(): Boolean = recorder.isRecording()

    private fun validateAudioQuality(features: FloatArray) {
        val rms = features.getOrElse(0) { 0f }
        val clippingRatio = features.getOrElse(5) { 0f }
        val durationSec = features.getOrElse(7) { 0f }

        if (durationSec < MIN_DURATION_SEC) {
            throw IllegalStateException("Audio too short. Please record at least ${MIN_DURATION_SEC.toInt()} second(s).")
        }
        if (durationSec > MAX_DURATION_SEC) {
            throw IllegalStateException("Audio too long. Keep recording under ${MAX_DURATION_SEC.toInt()} seconds.")
        }
        if (rms < MIN_RMS) {
            throw IllegalStateException("Input volume is too low. Move closer to microphone and retry.")
        }
        if (clippingRatio > MAX_CLIPPING_RATIO) {
            throw IllegalStateException("Audio is clipped/noisy. Reduce volume and retry.")
        }
    }

    companion object {
        const val SAMPLE_RATE_HZ = 16_000
        private const val MIN_DURATION_SEC = 1.0f
        private const val MAX_DURATION_SEC = 15.0f
        private const val MIN_RMS = 0.01f
        private const val MAX_CLIPPING_RATIO = 0.35f
    }
}
