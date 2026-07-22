package com.vpsaker.fake_voice_detector.domain.model

data class AuthTelemetryEvent(
    val timestampMs: Long,
    val fileName: String?,
    val inputSource: String,
    val fileHash: String?,
    val sampleRateHz: Int,
    val originalSampleRateHz: Int,
    val channelCount: Int,
    val spoofProbability: Float,
    val threshold: Float,
    val predictedLabel: String,
    val decision: String,
    val reason: String,
    val modelName: String,
    val recordingDurationSec: Float,
    val confidence: Float,
    val meetsSpoofThreshold: Boolean,
    val featureExtractionMs: Long,
    val inferenceMs: Long,
    val acousticFeatures: AcousticFeatureSnapshot,
)
