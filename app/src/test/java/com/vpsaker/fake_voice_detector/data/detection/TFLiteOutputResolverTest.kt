package com.vpsaker.fake_voice_detector.data.detection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TFLiteOutputResolverTest {

    private val resolver = TFLiteOutputResolver()

    @Test
    fun `createOutputBufferForShape returns binary-class buffer for two-logit output`() {
        val buffer = resolver.createOutputBufferForShape(intArrayOf(1, 2))

        assertTrue(buffer is Array<*>)
        val values = (buffer as Array<*>)[0] as FloatArray
        assertEquals(2, values.size)
    }

    @Test
    fun `createOutputBufferForShape returns scalar buffer for single-value output`() {
        val buffer = resolver.createOutputBufferForShape(intArrayOf(1, 1))

        assertTrue(buffer is Array<*>)
        val values = (buffer as Array<*>)[0] as FloatArray
        assertEquals(1, values.size)
    }

    @Test
    fun `resolveSpoofScore normalizes probability pair`() {
        val score = resolver.resolveSpoofScore(floatArrayOf(0.8f, 0.2f))

        assertEquals(0.2f, score, 1e-6f)
    }

    @Test
    fun `resolveSpoofScore applies sigmoid to scalar logits`() {
        val score = resolver.resolveSpoofScore(floatArrayOf(-1f))

        assertEquals(0.26894143f, score, 1e-6f)
    }
}
