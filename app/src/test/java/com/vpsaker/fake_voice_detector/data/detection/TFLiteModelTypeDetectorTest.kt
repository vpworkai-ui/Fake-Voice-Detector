package com.vpsaker.fake_voice_detector.data.detection

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TFLiteModelTypeDetectorTest {

    private val detector = TFLiteModelTypeDetector()

    @Test
    fun `detectFromInputShapes returns single-input for one tensor`() {
        val modelType = detector.detectFromInputShapes(listOf(intArrayOf(1, 21)))

        assertTrue(modelType is TFLiteModelType.SingleInput)
        assertEquals(21, (modelType as TFLiteModelType.SingleInput).numFeatures)
    }

    @Test
    fun `detectFromInputShapes returns dual-input when spec and acoustic tensors are present`() {
        val modelType = detector.detectFromInputShapes(
            listOf(
                intArrayOf(1, 400, 80),
                intArrayOf(1, 8),
            ),
        )

        assertTrue(modelType is TFLiteModelType.DualInput)
        modelType as TFLiteModelType.DualInput
        assertEquals(400, modelType.specT)
        assertEquals(80, modelType.specF)
        assertEquals(8, modelType.numAcoustic)
    }

    @Test
    fun `detectFromInputShapes falls back to single-input when shapes are ambiguous`() {
        val modelType = detector.detectFromInputShapes(
            listOf(
                intArrayOf(1, 400, 80, 1),
                intArrayOf(1, 8, 1),
            ),
        )

        assertTrue(modelType is TFLiteModelType.SingleInput)
        assertEquals(1, (modelType as TFLiteModelType.SingleInput).numFeatures)
    }
}
