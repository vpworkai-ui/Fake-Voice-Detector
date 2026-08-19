package com.vpsaker.fake_voice_detector.data.detection

class TFLiteModelTypeDetector {

    fun detect(interpreter: TFLiteInterpreter): TFLiteModelType {
        val inputCount = interpreter.inputTensorCount
        val shapes = (0 until inputCount).map { interpreter.getInputTensor(it).shape }
        return detectFromInputShapes(shapes)
    }

    internal fun detectFromInputShapes(shapes: List<IntArray>): TFLiteModelType {
        if (shapes.size == 1) {
            return TFLiteModelType.SingleInput(shapes.first().last())
        }

        val specIndex = shapes.indexOfFirst { it.size == 3 }
        val acousticIndex = shapes.indexOfFirst { it.size == 2 }
        return if (specIndex >= 0 && acousticIndex >= 0) {
            TFLiteModelType.DualInput(
                specT = shapes[specIndex][1],
                specF = shapes[specIndex][2],
                numAcoustic = shapes[acousticIndex][1],
            )
        } else {
            TFLiteModelType.SingleInput(shapes.first().last())
        }
    }
}
