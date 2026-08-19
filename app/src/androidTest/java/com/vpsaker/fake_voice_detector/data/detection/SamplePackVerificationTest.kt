package com.vpsaker.fake_voice_detector.data.detection

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.usecase.EvaluateSpoofResultUseCase
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class SamplePackVerificationTest {

    @Test
    fun verifySamplePackMatchesExpectedLabels() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val appContext = instrumentation.targetContext.applicationContext
        val testAssets = instrumentation.context.assets

        val repository = VoiceSpoofingRepositoryImpl(
            recorder = NoopAudioRecorder,
            featureExtractor = AudioFeatureExtractor(),
            detectorEngine = TFLiteSpoofDetectorEngine(appContext),
            context = appContext,
            skipQualityChecksOnEmulator = true
        )
        val evaluate = EvaluateSpoofResultUseCase()
        val sampleFiles = testAssets.list("")
            ?.filter {
                it.matches(Regex("^(0[1-9]|1[0-8])_.*\\.wav$", RegexOption.IGNORE_CASE))
            }
            ?.sorted()
            .orEmpty()

        assertTrue("androidTest assets should include the 18-file sample pack", sampleFiles.size == 18)

        val rows = mutableListOf<String>()
        val mismatches = mutableListOf<String>()

        for (fileName in sampleFiles) {
            val expectedLabel = expectedLabelFor(fileName)
            val data = testAssets.open(fileName).use { it.readBytes() }
            val detection = runBlocking {
                repository.analyzeImportedAudio(fileName, data).getOrThrow()
            }
            val decision = evaluate(detection.spoofProbability, 0.25f).decision
            val expectedDecision = when (expectedLabel) {
                "spoof" -> AuthenticationDecision.BLOCK
                else -> AuthenticationDecision.ALLOW
            }
            val status = if (decision == expectedDecision) "OK" else "MISMATCH"
            rows += "%s\texpected=%s\tscore=%.6f\tdecision=%s\tfeatureMs=%d\tinferenceMs=%d".format(
                fileName,
                expectedLabel,
                detection.spoofProbability,
                decision,
                detection.featureExtractionMs,
                detection.inferenceMs
            )
            if (decision != expectedDecision) {
                mismatches += "$fileName expected=$expectedLabel actual=$decision score=${"%.6f".format(detection.spoofProbability)} [$status]"
            }
        }

        println("=== SAMPLE PACK VERIFICATION START ===")
        rows.forEach(::println)
        println("=== SAMPLE PACK VERIFICATION END ===")

        assertTrue(
            "Sample pack mismatches found:\n${mismatches.joinToString(separator = "\n")}",
            mismatches.isEmpty()
        )
    }

    private fun expectedLabelFor(fileName: String): String =
        if (fileName.contains("spoof", ignoreCase = true)) "spoof" else "bonafide"

    private object NoopAudioRecorder : AudioRecorder {
        override fun start(sampleRateHz: Int): Result<Unit> = Result.success(Unit)

        override fun stop(): ShortArray = ShortArray(0)

        override fun isRecording(): Boolean = false
    }
}
