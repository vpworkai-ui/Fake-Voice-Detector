package com.vpsaker.fake_voice_detector.data.audio

import kotlin.math.sqrt

class FrameActivityAnalyzer {

    data class FrameAnalysis(
        val activeDurationSec: Float,
        val noiseRms: Float,
        val totalFrames: Int,
        val activeFrames: Int,
    )

    fun analyze(signal: FloatArray, sampleRateHz: Int, vadThreshold: Float): FrameAnalysis {
        val frameSamples = (sampleRateHz / FRAMES_PER_SECOND).coerceAtLeast(1)
        var activeFrames = 0
        var totalFrames = 0
        var index = 0

        while (index + frameSamples <= signal.size) {
            if (frameRms(signal, index, frameSamples) > vadThreshold) {
                activeFrames++
            }
            totalFrames++
            index += frameSamples
        }

        val activeDurationSec = activeFrames.toFloat() * FRAME_DURATION_SEC
        val noiseRms = estimateNoiseRms(signal, frameSamples, vadThreshold, totalFrames, activeFrames)
        return FrameAnalysis(activeDurationSec, noiseRms, totalFrames, activeFrames)
    }

    private fun estimateNoiseRms(
        signal: FloatArray,
        frameSamples: Int,
        vadThreshold: Float,
        totalFrames: Int,
        activeFrames: Int,
    ): Float {
        if (totalFrames <= activeFrames) return MIN_NOISE_RMS

        var noiseSum = 0.0
        var noiseCount = 0
        var index = 0
        while (index + frameSamples <= signal.size) {
            val rms = frameRms(signal, index, frameSamples)
            if (rms <= vadThreshold) {
                noiseSum += rms * rms
                noiseCount++
            }
            index += frameSamples
        }
        return if (noiseCount > 0) sqrt(noiseSum / noiseCount).toFloat() else MIN_NOISE_RMS
    }

    private fun frameRms(signal: FloatArray, startIndex: Int, frameSamples: Int): Float {
        var sumSquares = 0.0
        for (offset in 0 until frameSamples) {
            val sample = signal[startIndex + offset]
            sumSquares += sample * sample
        }
        return sqrt(sumSquares / frameSamples).toFloat()
    }

    companion object {
        private const val FRAMES_PER_SECOND = 50
        private const val FRAME_DURATION_SEC = 0.02f
        private const val MIN_NOISE_RMS = 1e-6f
    }
}
