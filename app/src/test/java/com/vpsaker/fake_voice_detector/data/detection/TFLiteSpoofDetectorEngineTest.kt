package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class TFLiteSpoofDetectorEngineTest {

    @Test
    fun `detectSpoofProbability uses single-input path when model has one input`() {
        val fakeInterpreter = FakeInterpreter(
            inputTensors = listOf(TFLiteTensorInfo("feature_input", intArrayOf(1, 21))),
            outputTensors = listOf(TFLiteTensorInfo("output", intArrayOf(1, 1))),
            singleInputResponse = floatArrayOf(0.3f),
        )
        val engine = TFLiteSpoofDetectorEngine(
            context = null,
            interpreterLoader = FakeInterpreterLoader(fakeInterpreter),
        )

        val score = engine.detectSpoofProbability(validSpeechSamples(), sampleRateHz = 16_000)

        assertEquals(0.3f, score, 1e-6f)
        assertEquals(1, fakeInterpreter.singleInputRunCount)
        assertEquals(0, fakeInterpreter.multiInputRunCount)
        assertEquals(21, fakeInterpreter.lastSingleInput!!.size)
        assertEquals("tflite-single-input", engine.modelName)
    }

    @Test
    fun `detectSpoofProbability uses dual-input path when model has spectrogram and acoustic inputs`() {
        val fakeInterpreter = FakeInterpreter(
            inputTensors = listOf(
                TFLiteTensorInfo("spec_input", intArrayOf(1, 400, 80)),
                TFLiteTensorInfo("feature_input", intArrayOf(1, 8)),
            ),
            outputTensors = listOf(TFLiteTensorInfo("output", intArrayOf(1, 2))),
            multiInputResponse = floatArrayOf(0.2f, 0.8f),
        )
        val engine = TFLiteSpoofDetectorEngine(
            context = null,
            interpreterLoader = FakeInterpreterLoader(fakeInterpreter),
        )

        val score = engine.detectSpoofProbability(validSpeechSamples(), sampleRateHz = 16_000)

        assertEquals(0.8f, score, 1e-6f)
        assertEquals(0, fakeInterpreter.singleInputRunCount)
        assertEquals(1, fakeInterpreter.multiInputRunCount)

        val lastInputs = fakeInterpreter.lastMultiInputs!!
        val spectrogram = lastInputs[0] as Array<*>
        val acoustic = lastInputs[1] as Array<*>
        assertEquals(1, spectrogram.size)
        assertEquals(400, (spectrogram[0] as Array<*>).size)
        assertEquals(8, (acoustic[0] as FloatArray).size)
        assertTrue(((acoustic[0] as FloatArray)[AudioFeatureExtractor.RMS_INDEX]) > 0f)
        assertEquals("tflite-dual-input-spec+acoustic", engine.modelName)
    }

    private fun validSpeechSamples(): ShortArray {
        return ShortArray(16_000) { index ->
            if (index in 2_000..12_000) 6_000 else 0
        }
    }

    private class FakeInterpreterLoader(
        private val interpreter: TFLiteInterpreter,
    ) : TFLiteInterpreterLoader() {
        override fun load(context: Context?, modelAssetPath: String): TFLiteInterpreter = interpreter
    }

    private class FakeInterpreter(
        private val inputTensors: List<TFLiteTensorInfo>,
        private val outputTensors: List<TFLiteTensorInfo>,
        private val singleInputResponse: FloatArray = floatArrayOf(0.5f),
        private val multiInputResponse: FloatArray = floatArrayOf(0.5f),
    ) : TFLiteInterpreter {

        override val inputTensorCount: Int
            get() = inputTensors.size

        override val outputTensorCount: Int
            get() = outputTensors.size

        var singleInputRunCount: Int = 0
            private set
        var multiInputRunCount: Int = 0
            private set
        var lastSingleInput: FloatArray? = null
            private set
        var lastMultiInputs: Array<Any?>? = null
            private set

        override fun getInputTensor(index: Int): TFLiteTensorInfo = inputTensors[index]

        override fun getOutputTensor(index: Int): TFLiteTensorInfo = outputTensors[index]

        override fun run(input: FloatArray, output: Any) {
            singleInputRunCount++
            lastSingleInput = input.copyOf()
            val buffer = output as Array<*>
            val destination = buffer[0] as FloatArray
            for (index in destination.indices) {
                destination[index] = singleInputResponse[index]
            }
        }

        override fun runForMultipleInputsOutputs(inputs: Array<Any?>, outputs: Map<Int, Any>) {
            multiInputRunCount++
            lastMultiInputs = inputs.copyOf()
            val buffer = outputs.getValue(0) as Array<*>
            val destination = buffer[0] as FloatArray
            for (index in destination.indices) {
                destination[index] = multiInputResponse[index]
            }
        }
    }
}
