package com.vpsaker.fake_voice_detector.data.detection

import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

class VoiceSpoofingRepositoryImplTest {

    @Test
    fun `startRecording delegates configured sample rate to recorder`() = runBlocking {
        val recorder = FakeRecorder(ShortArray(0))
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector(),
            skipQualityChecksOnEmulator = false,
        )

        val result = repository.startRecording()

        assertTrue(result.isSuccess)
        assertEquals(16_000, recorder.lastStartSampleRateHz)
    }

    @Test
    fun `stopRecordingAndAnalyze fails when audio too short`() = runBlocking {
        val recorder = FakeRecorder(ShortArray(4_000) { 6_000 })
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector(),
            skipQualityChecksOnEmulator = false
        )

        val result = repository.stopRecordingAndAnalyze()

        assertTrue(result.isFailure)
    }

    @Test
    fun `stopRecordingAndAnalyze fails when volume too low`() = runBlocking {
        val recorder = FakeRecorder(ShortArray(16_000) { 1 })
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector(),
            skipQualityChecksOnEmulator = false
        )

        val result = repository.stopRecordingAndAnalyze()

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("volume is too low") == true)
    }

    @Test
    fun `stopRecordingAndAnalyze fails when no speech activity detected`() = runBlocking {
        val samples = ShortArray(16_000) { index ->
            if (index < 1_600) 6_000 else 0
        }
        val recorder = FakeRecorder(samples)
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = FakeDetector(),
            skipQualityChecksOnEmulator = false
        )

        val result = repository.stopRecordingAndAnalyze()

        assertTrue(result.isFailure)
        assertTrue(result.exceptionOrNull()?.message?.contains("No speech detected") == true)
    }

    @Test
    fun `stopRecordingAndAnalyze passes when speech activity exists`() = runBlocking {
        val samples = ShortArray(16_000) { index ->
            if (index in 2_000..12_000) 6_000 else 0
        }
        val recorder = FakeRecorder(samples)
        val detector = FakeDetector(probability = 0.1f)
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = recorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = detector,
            skipQualityChecksOnEmulator = false
        )

        val result = repository.stopRecordingAndAnalyze()

        val errorMessage = result.exceptionOrNull()?.message
        assertTrue(errorMessage ?: "expected success", result.isSuccess)
        val detection = result.getOrThrow()
        assertEquals(0.1f, detection.spoofProbability, 1e-6f)
        assertEquals("fake", detection.modelName)
        assertEquals(1.0f, detection.recordingDurationSec, 1e-4f)
        assertEquals(1, detector.callCount)
        assertEquals(16_000, detector.lastSampleRateHz)
        assertEquals(16_000, detector.lastPcmSize)
    }

    @Test
    fun `analyzeImportedAudio resamples wav to repository sample rate before inference`() = runBlocking {
        val sourceSamples = ShortArray(8_000) { index ->
            if (index in 1_000..6_000) 6_000 else 0
        }
        val detector = FakeDetector(probability = 0.2f)
        val repository = VoiceSpoofingRepositoryImpl(
            recorder = FakeRecorder(ShortArray(0)),
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = detector,
            skipQualityChecksOnEmulator = false,
        )

        val result = repository.analyzeImportedAudio(
            fileName = "sample.wav",
            data = buildMonoPcm16Wav(sourceSamples, sampleRateHz = 8_000),
        )

        assertTrue(result.isSuccess)
        val detection = result.getOrThrow()
        assertEquals(0.2f, detection.spoofProbability, 1e-6f)
        assertEquals(16_000, detector.lastSampleRateHz)
        assertEquals(16_000, detector.lastPcmSize)
        assertEquals(1.0f, detection.recordingDurationSec, 1e-4f)
    }

    private class FakeDetector(
        private val probability: Float = 0.1f,
    ) : SpoofDetectorEngine {
        override val modelName: String = "fake"

        var callCount: Int = 0
            private set
        var lastSampleRateHz: Int = -1
            private set
        var lastPcmSize: Int = -1
            private set

        override fun detectSpoofProbability(pcm: ShortArray, sampleRateHz: Int): Float {
            callCount++
            lastSampleRateHz = sampleRateHz
            lastPcmSize = pcm.size
            return probability
        }
    }

    private class FakeRecorder(
        private val data: ShortArray
    ) : AudioRecorder {
        var lastStartSampleRateHz: Int = -1
            private set

        override fun start(sampleRateHz: Int): Result<Unit> {
            lastStartSampleRateHz = sampleRateHz
            return Result.success(Unit)
        }

        override fun stop(): ShortArray = data
        override fun isRecording(): Boolean = false
    }

    private fun buildMonoPcm16Wav(samples: ShortArray, sampleRateHz: Int): ByteArray {
        val channels = 1
        val bitsPerSample = 16
        val byteRate = sampleRateHz * channels * bitsPerSample / 8
        val blockAlign = channels * bitsPerSample / 8
        val pcmBytes = ByteArray(samples.size * 2)
        ByteBuffer.wrap(pcmBytes).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer().put(samples)

        val out = ByteArrayOutputStream()
        fun writeAscii(value: String) = out.write(value.toByteArray(Charsets.US_ASCII))
        fun writeLeInt(value: Int) = out.write(ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array())
        fun writeLeShort(value: Int) = out.write(ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(value.toShort()).array())

        writeAscii("RIFF")
        writeLeInt(36 + pcmBytes.size)
        writeAscii("WAVE")
        writeAscii("fmt ")
        writeLeInt(16)
        writeLeShort(1)
        writeLeShort(channels)
        writeLeInt(sampleRateHz)
        writeLeInt(byteRate)
        writeLeShort(blockAlign)
        writeLeShort(bitsPerSample)
        writeAscii("data")
        writeLeInt(pcmBytes.size)
        out.write(pcmBytes)
        return out.toByteArray()
    }
}
