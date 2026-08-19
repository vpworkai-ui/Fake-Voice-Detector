package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.abs
import kotlin.math.sqrt

class AcousticFeatureExtractor(
    private val normalizer: PcmAudioNormalizer = PcmAudioNormalizer(),
) {

    fun extract(
        audioPcm: ShortArray,
        sampleRateHz: Int,
        targetSampleCount: Int? = null,
    ): FloatArray {
        if (audioPcm.isEmpty()) return FloatArray(AudioFeatureExtractor.ACOUSTIC_FEATURE_COUNT)
        return extract(normalizer.normalize(audioPcm, targetSampleCount), sampleRateHz)
    }

    fun extract(signal: FloatArray, sampleRateHz: Int): FloatArray {
        if (signal.isEmpty()) return FloatArray(AudioFeatureExtractor.ACOUSTIC_FEATURE_COUNT)

        var sumSquares = 0.0
        var sumAbs = 0.0
        var peak = 0f
        var minValue = Float.POSITIVE_INFINITY
        var maxValue = Float.NEGATIVE_INFINITY
        var zeroCrossings = 0
        var previous = signal[0]
        val sampleCount = signal.size

        for (index in signal.indices) {
            val sample = signal[index]
            val absolute = abs(sample)
            sumSquares += sample * sample
            sumAbs += absolute
            if (absolute > peak) peak = absolute
            if (sample < minValue) minValue = sample
            if (sample > maxValue) maxValue = sample
            if (index > 0 && hasSignChange(previous, sample)) zeroCrossings++
            previous = sample
        }

        val rms = sqrt((sumSquares / sampleCount).toFloat())
        val meanAbs = (sumAbs / sampleCount).toFloat()
        val zcr = if (sampleCount > 1) zeroCrossings.toFloat() / (sampleCount - 1) else 0f
        val crestFactor = if (rms > EPS) (peak / rms).coerceIn(0f, MAX_CREST_FACTOR) else 0f

        var clippedSamples = 0
        for (sample in signal) {
            if (abs(sample) > CLIPPING_THRESHOLD) clippedSamples++
        }
        val clippingRatio = clippedSamples.toFloat() / sampleCount
        val dynamicRange = (maxValue - minValue).coerceAtLeast(0f)
        val durationSec = sampleCount.toFloat() / sampleRateHz

        return floatArrayOf(
            rms,
            meanAbs,
            zcr,
            peak,
            crestFactor,
            clippingRatio,
            dynamicRange,
            durationSec,
        )
    }

    private fun hasSignChange(previous: Float, current: Float): Boolean {
        return (previous >= 0f && current < 0f) || (previous < 0f && current >= 0f)
    }

    companion object {
        private const val EPS = 1e-6f
        private const val CLIPPING_THRESHOLD = 0.98f
        private const val MAX_CREST_FACTOR = 10f
    }
}
