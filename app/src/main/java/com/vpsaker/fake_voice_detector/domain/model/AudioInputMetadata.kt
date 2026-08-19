package com.vpsaker.fake_voice_detector.domain.model

data class AudioInputMetadata(
    val inputSource: String = "unknown",
    val fileName: String? = null,
    val fileHash: String? = null,
    val originalSampleRateHz: Int = 0,
    val normalizedSampleRateHz: Int = 0,
    val channelCount: Int = 0,
)

