package com.vpsaker.fake_voice_detector.data.detection

/**
 * Facade used by app code that still wants one entry point for audio features.
 *
 * The actual DSP responsibilities are delegated to smaller collaborators:
 * - [PcmAudioNormalizer] for PCM -> Float normalization
 * - [AcousticFeatureExtractor] for the 8 runtime acoustic features
 * - [MfccFeatureExtractor] for the 13 MFCC coefficients used by historical 21-feature models
 *
 * Feature order (must match Python training scripts exactly):
 *   [0]  RMS
 *   [1]  MeanAbs
 *   [2]  ZCR
 *   [3]  Peak
 *   [4]  CrestFactor
 *   [5]  ClippingRatio
 *   [6]  DynamicRange
 *   [7]  DurationSec
 *   [8]..[20] MFCC mean coefficients 1..13
 *
 * Important: index [7] reflects current Android runtime behavior, which is
 * total clip duration in seconds. Historical reports and some ML scripts may
 * still refer to this slot as ActiveDuration, but that is not the exact
 * implementation used by the deployed app today.
 */
class AudioFeatureExtractor(
    private val normalizer: PcmAudioNormalizer = PcmAudioNormalizer(),
    private val acousticFeatureExtractor: AcousticFeatureExtractor = AcousticFeatureExtractor(normalizer),
    private val mfccFeatureExtractor: MfccFeatureExtractor = MfccFeatureExtractor(),
) {

    fun extractFullFeatureVector(audioPcm: ShortArray, sampleRateHz: Int): FloatArray {
        if (audioPcm.isEmpty()) return FloatArray(FULL_FEATURE_COUNT)

        val signal = normalizer.normalize(audioPcm)
        val acoustic = acousticFeatureExtractor.extract(signal, sampleRateHz)
        val mfcc = mfccFeatureExtractor.extractMean(signal, sampleRateHz)
        return acoustic + mfcc
    }

    @Deprecated(
        message = "Use extractFullFeatureVector() for 21-feature models or extractAcousticFeatures() for deployed dual-input models.",
        replaceWith = ReplaceWith("extractFullFeatureVector(audioPcm, sampleRateHz)"),
    )
    fun extractFeatures(audioPcm: ShortArray, sampleRateHz: Int): FloatArray {
        return extractFullFeatureVector(audioPcm, sampleRateHz)
    }

    fun extractAcousticFeatures(
        audioPcm: ShortArray,
        sampleRateHz: Int,
        targetSampleCount: Int? = null,
    ): FloatArray {
        // When targetSampleCount is provided, the caller is intentionally asking
        // for deploy-model parity where short clips are zero-padded to a fixed
        // analysis window before acoustic statistics are computed.
        return acousticFeatureExtractor.extract(audioPcm, sampleRateHz, targetSampleCount)
    }

    fun normalizePcm(audioPcm: ShortArray, targetSampleCount: Int? = null): FloatArray {
        return normalizer.normalize(audioPcm, targetSampleCount)
    }

    companion object {
        const val RMS_INDEX = 0
        const val MEAN_ABS_INDEX = 1
        const val ZCR_INDEX = 2
        const val PEAK_INDEX = 3
        const val CREST_FACTOR_INDEX = 4
        const val CLIPPING_RATIO_INDEX = 5
        const val DYNAMIC_RANGE_INDEX = 6
        const val DURATION_SEC_INDEX = 7

        const val ACOUSTIC_FEATURE_COUNT = 8
        const val FULL_FEATURE_COUNT = 21

        @Deprecated("Use FULL_FEATURE_COUNT instead.")
        const val FEATURE_SIZE = FULL_FEATURE_COUNT
    }
}
