package com.vpsaker.fake_voice_detector.domain.model

import kotlin.math.abs

data class DetectionResult(
    val spoofProbability: Float,
    val threshold: Float = DEFAULT_THRESHOLD,
    val modelName: String,
    val recordingDurationSec: Float,
    val featureExtractionMs: Long = 0L,
    val inferenceMs: Long = 0L,
    val inputMetadata: AudioInputMetadata = AudioInputMetadata(),
    val acousticFeatures: AcousticFeatureSnapshot = AcousticFeatureSnapshot(),
) {
    val isSpoof: Boolean = spoofProbability >= threshold
    val confidence: Float = (abs(spoofProbability - threshold) * 2f).coerceIn(0f, 1f)

    companion object {
        const val DEFAULT_THRESHOLD: Float = 0.25f
    }
}
