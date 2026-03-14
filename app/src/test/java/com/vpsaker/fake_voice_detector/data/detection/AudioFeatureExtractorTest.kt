package com.vpsaker.fake_voice_detector.data.detection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioFeatureExtractorTest {

    private val extractor = AudioFeatureExtractor()

    @Test
    fun `extractFeatures returns expected size`() {
        val signal = ShortArray(16_000) { index ->
            if (index % 40 < 20) Short.MAX_VALUE else Short.MIN_VALUE
        }

        val features = extractor.extractFeatures(signal, sampleRateHz = 16_000)

        assertEquals(AudioFeatureExtractor.FEATURE_SIZE, features.size)
        assertTrue(features[0] > 0f)
        assertTrue(features[2] > 0.01f)
    }

    @Test
    fun `extractFeatures handles empty audio`() {
        val features = extractor.extractFeatures(ShortArray(0), sampleRateHz = 16_000)
        assertEquals(AudioFeatureExtractor.FEATURE_SIZE, features.size)
        assertTrue(features.all { it == 0f })
    }
}
