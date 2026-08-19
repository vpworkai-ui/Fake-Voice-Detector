package com.vpsaker.fake_voice_detector.domain.model

data class AcousticFeatureSnapshot(
    val rms: Float = 0f,
    val meanAbs: Float = 0f,
    val zcr: Float = 0f,
    val peak: Float = 0f,
    val crestFactor: Float = 0f,
    val clippingRatio: Float = 0f,
    val dynamicRange: Float = 0f,
    val durationSec: Float = 0f,
)

