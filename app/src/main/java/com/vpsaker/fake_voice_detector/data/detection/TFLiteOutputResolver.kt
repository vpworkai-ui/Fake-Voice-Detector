package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.exp

class TFLiteOutputResolver {

    fun createOutputBuffer(interpreter: TFLiteInterpreter): Any {
        return createOutputBufferForShape(interpreter.getOutputTensor(0).shape)
    }

    internal fun createOutputBufferForShape(outputShape: IntArray): Any {
        return if (outputShape.contentEquals(intArrayOf(1, 2))) {
            Array(1) { FloatArray(2) }
        } else {
            Array(1) { FloatArray(1) }
        }
    }

    fun resolveFromSingleInputRun(interpreter: TFLiteInterpreter, input: FloatArray): Float {
        return when (val output = createOutputBuffer(interpreter)) {
            is Array<*> -> {
                interpreter.run(input, output)
                resolveSpoofScore(output[0] as FloatArray)
            }
            else -> error("Unexpected output buffer type: ${output::class.java.simpleName}")
        }
    }

    fun resolveSpoofScore(raw: FloatArray): Float {
        if (raw.isEmpty()) return 0.5f
        return when (raw.size) {
            1 -> {
                val value = raw[0]
                if (value in 0f..1f) value else sigmoid(value)
            }
            2 -> {
                val bonafide = raw[0]
                val spoof = raw[1]
                if (bonafide in 0f..1f && spoof in 0f..1f) {
                    val sum = bonafide + spoof
                    if (sum > 1e-6f) (spoof / sum).coerceIn(0f, 1f) else 0.5f
                } else {
                    val bonafideExp = exp(bonafide)
                    val spoofExp = exp(spoof)
                    (spoofExp / (bonafideExp + spoofExp)).coerceIn(0f, 1f)
                }
            }
            else -> {
                val value = raw.last()
                if (value in 0f..1f) value else sigmoid(value)
            }
        }
    }

    private fun sigmoid(value: Float): Float {
        return (1f / (1f + exp(-value))).coerceIn(0f, 1f)
    }
}
