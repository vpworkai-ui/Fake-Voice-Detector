package com.vpsaker.fake_voice_detector.data.detection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioFeatureExtractorTest {

    private val extractor = AudioFeatureExtractor()

    @Test
    fun `extractFullFeatureVector returns expected size`() {
        val signal = ShortArray(16_000) { index ->
            if (index % 40 < 20) Short.MAX_VALUE else Short.MIN_VALUE
        }

        val features = extractor.extractFullFeatureVector(signal, sampleRateHz = 16_000)

        assertEquals(AudioFeatureExtractor.FULL_FEATURE_COUNT, features.size)
        assertTrue(features[0] > 0f)
        assertTrue(features[2] > 0.01f)
    }

    @Test
    fun `extractFullFeatureVector handles empty audio`() {
        val features = extractor.extractFullFeatureVector(ShortArray(0), sampleRateHz = 16_000)
        assertEquals(AudioFeatureExtractor.FULL_FEATURE_COUNT, features.size)
        assertTrue(features.all { it == 0f })
    }

    @Test
    fun `extractAcousticFeatures returns expected size and duration`() {
        val signal = ShortArray(8_000) { Short.MAX_VALUE }

        val features = extractor.extractAcousticFeatures(signal, sampleRateHz = 16_000)

        assertEquals(AudioFeatureExtractor.ACOUSTIC_FEATURE_COUNT, features.size)
        assertEquals(0.5f, features[7], 1e-4f)
        assertTrue(features[0] > 0f)
    }

    @Test
    fun `extractAcousticFeatures respects target sample padding`() {
        val signal = ShortArray(8_000) { index -> if (index % 2 == 0) Short.MAX_VALUE else Short.MIN_VALUE }

        val rawFeatures = extractor.extractAcousticFeatures(signal, sampleRateHz = 16_000)
        val paddedFeatures = extractor.extractAcousticFeatures(
            audioPcm = signal,
            sampleRateHz = 16_000,
            targetSampleCount = 16_000,
        )

        assertEquals(0.5f, rawFeatures[7], 1e-4f)
        assertEquals(1.0f, paddedFeatures[7], 1e-4f)
        assertNotEquals(rawFeatures[0], paddedFeatures[0], 1e-6f)
    }
}
