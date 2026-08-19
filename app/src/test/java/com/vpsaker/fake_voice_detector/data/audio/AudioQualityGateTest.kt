package com.vpsaker.fake_voice_detector.data.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class AudioQualityGateTest {

    @Test
    fun `check rejects empty recordings`() {
        val result = AudioQualityGate.check(ShortArray(0), sampleRateHz = 16_000)

        assertFalse(result.passed)
        assertEquals("empty_recording", result.reason)
        assertEquals(0f, result.activeDurationSec, 1e-6f)
    }

    @Test
    fun `check rejects very quiet audio`() {
        val result = AudioQualityGate.check(
            pcm = ShortArray(16_000) { 1 },
            sampleRateHz = 16_000,
        )

        assertFalse(result.passed)
        assertTrue(result.reason.contains("too_quiet"))
    }

    @Test
    fun `check rejects audio without enough active speech`() {
        val samples = ShortArray(16_000) { index ->
            if (index < 1_600) 6_000 else 0
        }

        val result = AudioQualityGate.check(samples, sampleRateHz = 16_000)

        assertFalse(result.passed)
        assertTrue(result.reason.contains("too_short"))
        assertTrue(result.activeDurationSec < AudioQualityGate.MIN_DURATION_SEC)
    }

    @Test
    fun `check accepts clean speech with enough active duration`() {
        val samples = ShortArray(16_000) { 6_000 }

        val result = AudioQualityGate.check(samples, sampleRateHz = 16_000)

        assertTrue(result.passed)
        assertEquals("ok", result.reason)
        assertTrue(result.activeDurationSec >= AudioQualityGate.MIN_DURATION_SEC)
        assertTrue(result.rmsdB > AudioQualityGate.MIN_RMS_DBF)
    }
}
