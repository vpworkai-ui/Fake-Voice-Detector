package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.abs
import kotlin.math.sqrt

class AudioFeatureExtractor {

    fun extractFeatures(audioPcm: ShortArray, sampleRateHz: Int): FloatArray {
        if (audioPcm.isEmpty()) {
            return FloatArray(FEATURE_SIZE)
        }

        val normalized = FloatArray(audioPcm.size) { index ->
            audioPcm[index] / Short.MAX_VALUE.toFloat()
        }

        val rms = sqrt(normalized.map { it * it }.average().toFloat())
        val meanAbs = normalized.map { abs(it) }.average().toFloat()
        val zcr = zeroCrossingRate(normalized)
        val peak = normalized.maxOf { abs(it) }
        val crestFactor = if (rms > EPS) peak / rms else 0f
        val clippingRatio = normalized.count { abs(it) > 0.98f }.toFloat() / normalized.size
        val dynamicRange = dynamicRange(normalized)
        val durationSec = audioPcm.size.toFloat() / sampleRateHz.toFloat()

        return floatArrayOf(
            rms,
            meanAbs,
            zcr,
            peak,
            crestFactor.coerceIn(0f, 10f),
            clippingRatio,
            dynamicRange,
            durationSec
        )
    }

    private fun zeroCrossingRate(signal: FloatArray): Float {
        if (signal.size < 2) return 0f

        var crossings = 0
        var prev = signal.first()
        for (i in 1 until signal.size) {
            val current = signal[i]
            if ((prev >= 0f && current < 0f) || (prev < 0f && current >= 0f)) {
                crossings++
            }
            prev = current
        }
        return crossings.toFloat() / (signal.size - 1)
    }

    private fun dynamicRange(signal: FloatArray): Float {
        var min = Float.POSITIVE_INFINITY
        var max = Float.NEGATIVE_INFINITY
        signal.forEach {
            if (it < min) min = it
            if (it > max) max = it
        }
        return (max - min).coerceAtLeast(0f)
    }

    companion object {
        private const val EPS = 1e-6f
        const val FEATURE_SIZE = 8
    }
}
