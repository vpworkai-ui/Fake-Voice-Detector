package com.vpsaker.fake_voice_detector.data.detection

sealed interface TFLiteModelType {
    data class SingleInput(val numFeatures: Int) : TFLiteModelType
    data class DualInput(val specT: Int, val specF: Int, val numAcoustic: Int) : TFLiteModelType
}
