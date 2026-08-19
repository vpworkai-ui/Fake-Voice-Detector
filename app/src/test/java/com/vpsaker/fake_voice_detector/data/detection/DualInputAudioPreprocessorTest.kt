package com.vpsaker.fake_voice_detector.data.detection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class DualInputAudioPreprocessorTest {

    private val preprocessor = DualInputAudioPreprocessor()

    @Test
    fun `buildAcousticInput pads output to requested feature width`() {
        val audio = ShortArray(8_000) { Short.MAX_VALUE }

        val acousticInput = preprocessor.buildAcousticInput(audio, sampleRateHz = 16_000, numAcoustic = 12)

        assertEquals(1, acousticInput.size)
        assertEquals(12, acousticInput[0].size)
        assertTrue(acousticInput[0][0] > 0f)
        assertEquals(0f, acousticInput[0][11], 1e-6f)
    }

    @Test
    fun `buildAcousticInput uses fixed duration window for short clips`() {
        val audio = ShortArray(8_000) { Short.MAX_VALUE }

        val acousticInput = preprocessor.buildAcousticInput(audio, sampleRateHz = 16_000, numAcoustic = 8)

        assertEquals(4f, acousticInput[0][AudioFeatureExtractor.DURATION_SEC_INDEX], 1e-4f)
    }

    @Test
    fun `buildSpectrogramInput returns requested frame and bin dimensions`() {
        val audio = ShortArray(16_000) { index -> if (index % 2 == 0) Short.MAX_VALUE else Short.MIN_VALUE }

        val specInput = preprocessor.buildSpectrogramInput(
            audioPcm = audio,
            sampleRateHz = 16_000,
            targetFrames = 400,
            targetBins = 80,
        )

        assertEquals(1, specInput.size)
        assertEquals(400, specInput[0].size)
        assertEquals(80, specInput[0][0].size)
    }
}
