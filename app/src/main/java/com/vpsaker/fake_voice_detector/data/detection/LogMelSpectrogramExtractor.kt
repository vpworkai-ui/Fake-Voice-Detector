package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sin

class LogMelSpectrogramExtractor(
    private val normalizer: PcmAudioNormalizer = PcmAudioNormalizer(),
) {

    fun extract(
        audioPcm: ShortArray,
        sampleRateHz: Int,
        targetSampleCount: Int = sampleRateHz * DEFAULT_MAX_AUDIO_DURATION_SEC,
        targetFrames: Int = DEFAULT_TARGET_FRAMES,
        targetBins: Int = DEFAULT_TARGET_BINS,
    ): Array<Array<FloatArray>> {
        val signal = normalizer.normalize(audioPcm, targetSampleCount)
        return extract(signal, sampleRateHz, targetFrames, targetBins)
    }

    fun extract(
        signal: FloatArray,
        sampleRateHz: Int,
        targetFrames: Int = DEFAULT_TARGET_FRAMES,
        targetBins: Int = DEFAULT_TARGET_BINS,
    ): Array<Array<FloatArray>> {
        val frameLength = FRAME_LENGTH
        val frameStep = FRAME_STEP
        val numBins = frameLength / 2 + 1
        val window = FloatArray(frameLength) { index ->
            (0.5 - 0.5 * cos(2.0 * PI * index / frameLength)).toFloat()
        }
        val melFilterBank = buildMelFilterbank(targetBins, numBins, sampleRateHz)

        val frames = Array(targetFrames) { FloatArray(targetBins) }
        var frameIndex = 0
        var start = 0
        while (frameIndex < targetFrames && start < signal.size) {
            val frame = FloatArray(frameLength)
            var index = 0
            while (index < frameLength) {
                val sampleIndex = start + index
                val sample = if (sampleIndex < signal.size) signal[sampleIndex] else 0f
                frame[index] = sample * window[index]
                index++
            }

            val power = fftPower(frame)
            val melEnergy = FloatArray(targetBins)
            var filterIndex = 0
            while (filterIndex < targetBins) {
                var energy = 0f
                var binIndex = 0
                while (binIndex < numBins) {
                    energy += melFilterBank[filterIndex][binIndex] * power[binIndex]
                    binIndex++
                }
                melEnergy[filterIndex] = ln(energy + LOG_EPS)
                filterIndex++
            }
            frames[frameIndex] = melEnergy
            frameIndex++
            start += frameStep
        }

        return Array(1) { Array(targetFrames) { frameIdx -> frames[frameIdx] } }
    }

    private fun buildMelFilterbank(numMel: Int, numBins: Int, sampleRateHz: Int): Array<FloatArray> {
        fun hzToMel(hz: Double) = 1127.0 * ln(1.0 + hz / 700.0)

        val lowerEdgeHz = 80.0
        val upperEdgeHz = min(7600.0, sampleRateHz / 2.0)
        val nyquistHz = sampleRateHz / 2.0
        val zero = 0.0
        val bandsToZero = 1

        val linearFrequenciesHz = DoubleArray(numBins - bandsToZero) { index ->
            val fftBin = index + bandsToZero
            zero + (nyquistHz - zero) * fftBin / (numBins - 1).toDouble()
        }
        val spectrogramBinsMel = DoubleArray(linearFrequenciesHz.size) { index ->
            hzToMel(linearFrequenciesHz[index])
        }

        val lowerEdgeMel = hzToMel(lowerEdgeHz)
        val upperEdgeMel = hzToMel(upperEdgeHz)
        val bandEdgeStep = (upperEdgeMel - lowerEdgeMel) / (numMel + 1).toDouble()

        val melWeights = Array(numMel) { FloatArray(numBins) }
        for (melBand in 0 until numMel) {
            val lowerMel = lowerEdgeMel + melBand * bandEdgeStep
            val centerMel = lowerMel + bandEdgeStep
            val upperMel = centerMel + bandEdgeStep

            for (binOffset in spectrogramBinsMel.indices) {
                val mel = spectrogramBinsMel[binOffset]
                val lowerSlope = (mel - lowerMel) / (centerMel - lowerMel)
                val upperSlope = (upperMel - mel) / (upperMel - centerMel)
                val weight = max(0.0, min(lowerSlope, upperSlope)).toFloat()
                melWeights[melBand][binOffset + bandsToZero] = weight
            }
        }

        return melWeights
    }

    private fun fftPower(frame: FloatArray): FloatArray {
        val size = frame.size
        val real = frame.copyOf()
        val imaginary = FloatArray(size)

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
            val twiddleReal = cos(angle).toFloat()
            val twiddleImaginary = sin(angle).toFloat()
            var offset = 0
            while (offset < size) {
                var currentReal = 1f
                var currentImaginary = 0f
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

        val outputBins = size / 2 + 1
        return FloatArray(outputBins) { index -> real[index] * real[index] + imaginary[index] * imaginary[index] }
    }

    companion object {
        const val DEFAULT_MAX_AUDIO_DURATION_SEC = 4
        const val DEFAULT_TARGET_FRAMES = 400
        const val DEFAULT_TARGET_BINS = 80

        private const val FRAME_LENGTH = 512
        private const val FRAME_STEP = 160
        private const val LOG_EPS = 1e-6f
    }
}
