package com.vpsaker.fake_voice_detector.data.audio

import kotlin.math.log10
import kotlin.math.sqrt

/**
 * Checks recording quality before running the spoof-detection model.
 *
 * Rejects samples that are too short, too quiet, or too noisy so the model
 * never receives bad input that would cause false positives / false negatives.
 */
object AudioQualityGate {

    data class QualityResult(
        val passed: Boolean,
        val reason: String,
        val rmsdB: Float,
        val snrEstimateDB: Float,
        val activeDurationSec: Float,
    )

    private val signalNormalizer = PcmSignalNormalizer()
    private val frameActivityAnalyzer = FrameActivityAnalyzer()

    /**
     * @param pcm             Raw PCM samples (16-bit normalised to [-1, 1] internally)
     * @param sampleRateHz    Recording sample rate
     * @param minDurationSec  Minimum active (non-silent) speech duration required
     * @param minRmsdB        Minimum signal level in dBFS (-60 dBFS = very quiet)
     * @param minSnrDB        Minimum estimated SNR (signal vs. background noise floor)
     */
    fun check(
        pcm: ShortArray,
        sampleRateHz: Int,
        minDurationSec: Float = MIN_DURATION_SEC,
        minRmsdB: Float = MIN_RMS_DBF,
        minSnrDB: Float = MIN_SNR_DB,
    ): QualityResult {
        if (pcm.isEmpty()) {
            return QualityResult(false, "empty_recording", -100f, 0f, 0f)
        }

        val signal = signalNormalizer.normalize(pcm)
        val rms = computeRms(signal)
        val rmsdB = toDbfs(rms)
        if (rmsdB < minRmsdB) {
            return QualityResult(
                passed = false,
                reason = "too_quiet (${rmsdB.toInt()} dBFS < ${minRmsdB.toInt()} dBFS)",
                rmsdB = rmsdB,
                snrEstimateDB = 0f,
                activeDurationSec = 0f,
            )
        }

        val vadThreshold = rms * VAD_RMS_RATIO
        val frameAnalysis = frameActivityAnalyzer.analyze(signal, sampleRateHz, vadThreshold)
        if (frameAnalysis.activeDurationSec < minDurationSec) {
            return QualityResult(
                passed = false,
                reason = "too_short (${String.format("%.2f", frameAnalysis.activeDurationSec)}s active < ${minDurationSec}s required)",
                rmsdB = rmsdB,
                snrEstimateDB = 0f,
                activeDurationSec = frameAnalysis.activeDurationSec,
            )
        }

        val snrDB = estimateSnrDb(rms, frameAnalysis.noiseRms)
        if (snrDB < minSnrDB) {
            return QualityResult(
                passed = false,
                reason = "too_noisy (SNR ${snrDB.toInt()} dB < ${minSnrDB.toInt()} dB required)",
                rmsdB = rmsdB,
                snrEstimateDB = snrDB,
                activeDurationSec = frameAnalysis.activeDurationSec,
            )
        }

        return QualityResult(true, "ok", rmsdB, snrDB, frameAnalysis.activeDurationSec)
    }

    private fun computeRms(signal: FloatArray): Float {
        var sumSquares = 0.0
        for (sample in signal) {
            sumSquares += sample * sample
        }
        return sqrt(sumSquares / signal.size).toFloat()
    }

    private fun toDbfs(rms: Float): Float {
        return if (rms > MIN_RMS_LINEAR) 20f * log10(rms) else MIN_DBFS
    }

    private fun estimateSnrDb(signalRms: Float, noiseRms: Float): Float {
        return if (noiseRms > MIN_RMS_LINEAR) 20f * log10(signalRms / noiseRms) else MAX_SNR_DB
    }

    const val MIN_DURATION_SEC = 1.0f
    const val MIN_RMS_DBF = -45f
    const val MIN_SNR_DB = 8f

    private const val VAD_RMS_RATIO = 0.20f
    private const val MIN_RMS_LINEAR = 1e-9f
    private const val MIN_DBFS = -100f
    private const val MAX_SNR_DB = 60f
}
