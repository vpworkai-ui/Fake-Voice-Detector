package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import org.tensorflow.lite.Interpreter
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import kotlin.math.exp

class TFLiteSpoofDetectorEngine(
    private val context: Context,
    private val modelAssetPath: String = DEFAULT_MODEL_PATH,
    private val allowHeuristicFallback: Boolean = true
) : SpoofDetectorEngine {

    override val modelName: String
        get() = if (interpreter != null) "tflite-voice-spoof-detector" else "missing-model"

    private val interpreter: Interpreter? by lazy {
        runCatching {
            val buffer = loadModelFile(context, modelAssetPath)
            Interpreter(buffer, Interpreter.Options())
        }.getOrNull()
    }

    override fun detectSpoofProbability(features: FloatArray): Float {
        val tflite = interpreter ?: return if (allowHeuristicFallback) {
            fallbackHeuristic(features)
        } else {
            throw IllegalStateException("Release mode requires a valid spoof detection model")
        }

        return runCatching {
            val inputSize = tflite.getInputTensor(0).shape().last().coerceAtLeast(1)
            val inputVector = FloatArray(inputSize)
            val copyLength = minOf(features.size, inputSize)
            for (index in 0 until copyLength) {
                inputVector[index] = features[index]
            }

            val outputSize = tflite.getOutputTensor(0).shape().last().coerceAtLeast(1)
            val output = Array(1) { FloatArray(outputSize) }
            tflite.run(arrayOf(inputVector), output)

            decodeOutput(output[0]).coerceIn(0f, 1f)
        }.getOrElse {
            if (allowHeuristicFallback) {
                fallbackHeuristic(features)
            } else {
                throw IllegalStateException("Spoof model inference failed in release mode", it)
            }
        }
    }

    private fun decodeOutput(raw: FloatArray): Float {
        if (raw.isEmpty()) return 0.5f

        if (raw.size == 1) {
            val value = raw[0]
            return if (value in 0f..1f) value else sigmoid(value)
        }

        val a = raw[0]
        val b = raw[1]
        return if (a in 0f..1f && b in 0f..1f) {
            val sum = a + b
            if (sum > 0f) b / sum else 0.5f
        } else {
            val expA = exp(a)
            val expB = exp(b)
            expB / (expA + expB)
        }
    }

    private fun fallbackHeuristic(features: FloatArray): Float {
        if (features.size < 8) return 0.5f

        val rms = features[0]
        val zcr = features[2]
        val crest = features[4]
        val clipping = features[5]
        val dynamicRange = features[6]

        val spoofLogit =
            (0.9f * zcr) +
            (0.5f * clipping) +
            (0.35f * (2f - dynamicRange).coerceAtLeast(0f)) +
            (0.15f * (crest / 5f).coerceIn(0f, 1f)) -
            (0.7f * rms)

        return sigmoid(spoofLogit)
    }

    private fun loadModelFile(context: Context, assetPath: String): MappedByteBuffer {
        val fileDescriptor = context.assets.openFd(assetPath)
        fileDescriptor.use { fd ->
            fd.createInputStream().channel.use { channel ->
                return channel.map(FileChannel.MapMode.READ_ONLY, fd.startOffset, fd.declaredLength)
            }
        }
    }

    private fun sigmoid(value: Float): Float = (1.0f / (1.0f + exp(-value))).toFloat()

    companion object {
        private const val DEFAULT_MODEL_PATH = "models/voice_spoof_detector.tflite"
    }
}
