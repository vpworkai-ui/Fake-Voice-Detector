package com.vpsaker.fake_voice_detector.data.telemetry

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import com.vpsaker.fake_voice_detector.data.detection.AudioFeatureExtractor
import com.vpsaker.fake_voice_detector.data.detection.TFLiteSpoofDetectorEngine
import com.vpsaker.fake_voice_detector.data.detection.VoiceSpoofingRepositoryImpl
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.usecase.EvaluateSpoofResultUseCase
import kotlinx.coroutines.runBlocking
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class StructuredTelemetrySmokeTest {

    @Test
    fun writesStructuredJsonForImportedFile() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val appContext = instrumentation.targetContext.applicationContext
        val testAssets = instrumentation.context.assets

        val repository = VoiceSpoofingRepositoryImpl(
            recorder = NoopAudioRecorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = TFLiteSpoofDetectorEngine(appContext),
            context = appContext,
            skipQualityChecksOnEmulator = true,
        )
        val telemetryRepository = FileTelemetryRepository(appContext)
        val evaluate = EvaluateSpoofResultUseCase()

        val fileName = "16_internet_spoof_01_vi.wav"
        val data = testAssets.open(fileName).use { it.readBytes() }
        val detection = runBlocking {
            repository.analyzeImportedAudio(fileName, data).getOrThrow()
        }
        val fusion = evaluate(detection.spoofProbability, 0.25f)
        val event = AuthTelemetryEvent(
            timestampMs = System.currentTimeMillis(),
            fileName = detection.inputMetadata.fileName,
            inputSource = detection.inputMetadata.inputSource,
            fileHash = detection.inputMetadata.fileHash,
            sampleRateHz = detection.inputMetadata.normalizedSampleRateHz,
            originalSampleRateHz = detection.inputMetadata.originalSampleRateHz,
            channelCount = detection.inputMetadata.channelCount,
            spoofProbability = detection.spoofProbability,
            threshold = fusion.spoofThreshold,
            predictedLabel = if (detection.isSpoof) "SPOOF" else "BONAFIDE",
            decision = fusion.decision.name,
            reason = fusion.reason,
            modelName = detection.modelName,
            recordingDurationSec = detection.recordingDurationSec,
            confidence = fusion.confidence,
            meetsSpoofThreshold = fusion.meetsSpoofThreshold,
            featureExtractionMs = detection.featureExtractionMs,
            inferenceMs = detection.inferenceMs,
            acousticFeatures = detection.acousticFeatures,
        )

        runBlocking {
            telemetryRepository.logAuthenticationEvent(event).getOrThrow()
        }

        val telemetryFile = appContext.filesDir.resolve("telemetry/voice_auth_events.jsonl")
        assertTrue("Telemetry log should be created", telemetryFile.exists())

        val lastLine = telemetryFile.readLines().last { it.isNotBlank() }
        val json = JSONObject(lastLine)

        assertEquals(fileName, json.getString("fileName"))
        assertEquals("imported_file", json.getString("inputSource"))
        assertEquals(16000, json.getInt("sampleRateHz"))
        assertEquals(16000, json.getInt("originalSampleRateHz"))
        assertEquals(1, json.getInt("channelCount"))
        assertTrue(json.has("spoofProbability"))
        assertTrue(json.has("threshold"))
        assertTrue(json.has("predictedLabel"))
        assertTrue(json.has("decision"))
        assertTrue(json.has("confidence"))
        assertTrue(json.has("featureExtractionMs"))
        assertTrue(json.has("inferenceMs"))

        val acoustic = json.getJSONObject("acousticFeatures")
        assertNotNull(acoustic)
        assertTrue(acoustic.has("rms"))
        assertTrue(acoustic.has("meanAbs"))
        assertTrue(acoustic.has("zcr"))
        assertTrue(acoustic.has("peak"))
        assertTrue(acoustic.has("crestFactor"))
        assertTrue(acoustic.has("clippingRatio"))
        assertTrue(acoustic.has("dynamicRange"))
        assertTrue(acoustic.has("durationSec"))

        println("STRUCTURED_TELEMETRY_JSON=$lastLine")
    }

    private object NoopAudioRecorder : AudioRecorder {
        override fun start(sampleRateHz: Int): Result<Unit> = Result.success(Unit)

        override fun stop(): ShortArray = ShortArray(0)

        override fun isRecording(): Boolean = false
    }
}
