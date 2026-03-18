package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AnalyzeVoiceSpoofingUseCaseTest {

    @Test
    fun `invoke returns repository analysis result`() = runBlocking {
        val expected = DetectionResult(
            spoofProbability = 0.73f,
            modelName = "unit-test-model",
            recordingDurationSec = 2.5f
        )
        val repository = FakeRepository(expected)
        val useCase = AnalyzeVoiceSpoofingUseCase(repository)

        val result = useCase()

        assertTrue(result.isSuccess)
        assertEquals(expected, result.getOrThrow())
    }

    private class FakeRepository(
        private val result: DetectionResult
    ) : VoiceSpoofingRepository {
        override suspend fun startRecording(): Result<Unit> = Result.success(Unit)

        override suspend fun stopRecordingAndAnalyze(): Result<DetectionResult> = Result.success(result)

        override suspend fun stopRecordingAndSaveSample(label: String): Result<String> {
            return Result.success("/tmp/fake_sample.wav")
        }

        override fun isRecording(): Boolean = false
    }
}
