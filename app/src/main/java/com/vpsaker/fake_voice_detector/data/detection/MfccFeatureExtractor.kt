package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.ln
import kotlin.math.log10
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.sin

class MfccFeatureExtractor {

    fun extractMean(signal: FloatArray, sampleRateHz: Int): FloatArray {
        if (signal.size < FRAME_LENGTH) return FloatArray(NUM_MFCC)

        val emphasized = FloatArray(signal.size)
        emphasized[0] = signal[0]
        for (index in 1 until signal.size) {
            emphasized[index] = signal[index] - PRE_EMPHASIS * signal[index - 1]
        }

        val hammingWindow = FloatArray(FRAME_LENGTH) { index ->
            (0.54 - 0.46 * cos(2.0 * PI * index / (FRAME_LENGTH - 1))).toFloat()
        }
        val melFilters = buildMelFilterbank(sampleRateHz)
        val fftSize = nextPowerOfTwo(FRAME_LENGTH)
        val nBins = fftSize / 2 + 1

        val mfccSum = DoubleArray(NUM_MFCC)
        var frameCount = 0
        var frameStart = 0
        while (frameStart + FRAME_LENGTH <= emphasized.size) {
            val real = DoubleArray(fftSize)
            val imaginary = DoubleArray(fftSize)
            for (index in 0 until FRAME_LENGTH) {
                real[index] = (emphasized[frameStart + index] * hammingWindow[index]).toDouble()
            }

            fft(real, imaginary)

            val powerSpectrum = DoubleArray(nBins) { bin ->
                real[bin] * real[bin] + imaginary[bin] * imaginary[bin]
            }
            val logMelEnergy = DoubleArray(NUM_MEL_FILTERS) { filterIndex ->
                var energy = 0.0
                for (bin in 0 until nBins) {
                    energy += melFilters[filterIndex][bin] * powerSpectrum[bin]
                }
                ln(energy + LOG_EPS)
            }

            for (mfccIndex in 0 until NUM_MFCC) {
                var coefficient = 0.0
                for (filterIndex in 0 until NUM_MEL_FILTERS) {
                    coefficient += logMelEnergy[filterIndex] *
                        cos(PI * mfccIndex * (filterIndex + 0.5) / NUM_MEL_FILTERS)
                }
                mfccSum[mfccIndex] += coefficient
            }

            frameCount++
            frameStart += HOP_LENGTH
        }

        if (frameCount == 0) return FloatArray(NUM_MFCC)
        return FloatArray(NUM_MFCC) { index -> (mfccSum[index] / frameCount).toFloat() }
    }

    private fun buildMelFilterbank(sampleRateHz: Int): Array<DoubleArray> {
        val fftSize = nextPowerOfTwo(FRAME_LENGTH)
        val nBins = fftSize / 2 + 1

        fun hzToMel(hz: Double) = 2595.0 * log10(1.0 + hz / 700.0)
        fun melToHz(mel: Double) = 700.0 * (10.0.pow(mel / 2595.0) - 1.0)

        val melLow = hzToMel(MEL_LOW_HZ)
        val melHigh = hzToMel(min(MEL_HIGH_HZ, sampleRateHz / 2.0))
        val melPoints = DoubleArray(NUM_MEL_FILTERS + 2) { index ->
            melToHz(melLow + index * (melHigh - melLow) / (NUM_MEL_FILTERS + 1))
        }
        val binPoints = DoubleArray(NUM_MEL_FILTERS + 2) { index ->
            floor((fftSize + 1) * melPoints[index] / sampleRateHz)
        }

        return Array(NUM_MEL_FILTERS) { filterIndex ->
            DoubleArray(nBins) { binIndex ->
                val bin = binIndex.toDouble()
                when {
                    bin < binPoints[filterIndex] -> 0.0
                    bin <= binPoints[filterIndex + 1] ->
                        (bin - binPoints[filterIndex]) /
                            (binPoints[filterIndex + 1] - binPoints[filterIndex] + LOG_EPS)
                    bin <= binPoints[filterIndex + 2] ->
                        (binPoints[filterIndex + 2] - bin) /
                            (binPoints[filterIndex + 2] - binPoints[filterIndex + 1] + LOG_EPS)
                    else -> 0.0
                }
            }
        }
    }

    private fun fft(real: DoubleArray, imaginary: DoubleArray) {
        val size = real.size
        var reversed = 0
        for (index in 1 until size) {
            var bit = size shr 1
            while (reversed and bit != 0) {
                reversed = reversed xor bit
                bit = bit shr 1
            }
            reversed = reversed xor bit
            if (index < reversed) {
                val tmpReal = real[index]
                real[index] = real[reversed]
                real[reversed] = tmpReal

                val tmpImaginary = imaginary[index]
                imaginary[index] = imaginary[reversed]
                imaginary[reversed] = tmpImaginary
            }
        }

        var len = 2
        while (len <= size) {
            val half = len / 2
            val angle = -2.0 * PI / len
            val twiddleReal = cos(angle)
            val twiddleImaginary = sin(angle)
            var offset = 0
            while (offset < size) {
                var currentReal = 1.0
                var currentImaginary = 0.0
                for (position in 0 until half) {
                    val evenReal = real[offset + position]
                    val evenImaginary = imaginary[offset + position]
                    val oddReal = real[offset + position + half] * currentReal -
                        imaginary[offset + position + half] * currentImaginary
                    val oddImaginary = real[offset + position + half] * currentImaginary +
                        imaginary[offset + position + half] * currentReal

                    real[offset + position] = evenReal + oddReal
                    imaginary[offset + position] = evenImaginary + oddImaginary
                    real[offset + position + half] = evenReal - oddReal
                    imaginary[offset + position + half] = evenImaginary - oddImaginary

                    val nextReal = currentReal * twiddleReal - currentImaginary * twiddleImaginary
                    currentImaginary = currentReal * twiddleImaginary + currentImaginary * twiddleReal
                    currentReal = nextReal
                }
                offset += len
            }
            len = len shl 1
        }
    }

    private fun nextPowerOfTwo(value: Int): Int {
        var power = 1
        while (power < value) power = power shl 1
        return power
    }

    companion object {
        private const val LOG_EPS = 1e-10
        private const val PRE_EMPHASIS = 0.97f
        private const val FRAME_LENGTH = 512
        private const val HOP_LENGTH = 160
        private const val NUM_MEL_FILTERS = 26
        private const val NUM_MFCC = 13
        private const val MEL_LOW_HZ = 80.0
        private const val MEL_HIGH_HZ = 7600.0
    }
}
