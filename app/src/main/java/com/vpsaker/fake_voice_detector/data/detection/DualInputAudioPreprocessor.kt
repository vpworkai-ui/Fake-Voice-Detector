package com.vpsaker.fake_voice_detector.data.detection

class DualInputAudioPreprocessor(
    private val featureExtractor: AudioFeatureExtractor = AudioFeatureExtractor(),
    private val logMelExtractor: LogMelSpectrogramExtractor = LogMelSpectrogramExtractor(),
    private val maxAudioDurationSec: Int = LogMelSpectrogramExtractor.DEFAULT_MAX_AUDIO_DURATION_SEC,
) {

    fun buildSpectrogramInput(
        audioPcm: ShortArray,
        sampleRateHz: Int,
        targetFrames: Int,
        targetBins: Int,
    ): Array<Array<FloatArray>> {
        return logMelExtractor.extract(
            audioPcm = audioPcm,
            sampleRateHz = sampleRateHz,
            targetSampleCount = sampleRateHz * maxAudioDurationSec,
            targetFrames = targetFrames,
            targetBins = targetBins,
        )
    }

    fun buildAcousticInput(audioPcm: ShortArray, sampleRateHz: Int, numAcoustic: Int): Array<FloatArray> {
        val acoustic = featureExtractor.extractAcousticFeatures(
            audioPcm = audioPcm,
            sampleRateHz = sampleRateHz,
            targetSampleCount = sampleRateHz * maxAudioDurationSec,
        )
        val padded = FloatArray(numAcoustic)
        for (index in 0 until minOf(acoustic.size, numAcoustic)) {
            padded[index] = acoustic[index]
        }
        return arrayOf(padded)
    }
}
