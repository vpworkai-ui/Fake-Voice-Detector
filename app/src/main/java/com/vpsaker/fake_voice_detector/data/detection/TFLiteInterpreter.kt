package com.vpsaker.fake_voice_detector.data.detection

interface TFLiteInterpreter {
    val inputTensorCount: Int
    val outputTensorCount: Int

    fun getInputTensor(index: Int): TFLiteTensorInfo
    fun getOutputTensor(index: Int): TFLiteTensorInfo
    fun run(input: FloatArray, output: Any)
    fun runForMultipleInputsOutputs(inputs: Array<Any?>, outputs: Map<Int, Any>)
}
