package com.vpsaker.fake_voice_detector.data.detection

import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Test

class VoiceSpoofingRepositoryImplTest {

    @Test
    fun `stopRecordingAndAnalyze fails when audio too short`() = runBlocking {
        val recorder = FakeRecorder(ShortArray(8_000) { 120 })
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector()
        )

        val result = repository.stopRecordingAndAnalyze()

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("Audio too short") == true)
    }

    @Test
    fun `stopRecordingAndAnalyze fails when volume too low`() = runBlocking {
        val recorder = FakeRecorder(ShortArray(16_000) { 1 })
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector()
        )

        val result = repository.stopRecordingAndAnalyze()

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("volume is too low") == true)
    }

    private class FakeDetector : SpoofDetectorEngine {
        override val modelName: String = "fake"
        override fun detectSpoofProbability(features: FloatArray): Float = 0.1f
    }

    private class FakeRecorder(
        private val data: ShortArray
    ) : AudioRecorder {
        override fun start(sampleRateHz: Int): Result<Unit> = Result.success(Unit)
        override fun stop(): ShortArray = data
        override fun isRecording(): Boolean = false
    }
}
