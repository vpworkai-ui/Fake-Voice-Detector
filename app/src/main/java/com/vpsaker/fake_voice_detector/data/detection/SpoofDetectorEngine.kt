package com.vpsaker.fake_voice_detector.data.detection

interface SpoofDetectorEngine {
    val modelName: String
    fun detectSpoofProbability(features: FloatArray): Float
}
