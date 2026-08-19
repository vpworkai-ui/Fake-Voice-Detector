package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import org.tensorflow.lite.Interpreter
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

open class TFLiteInterpreterLoader {

    open fun load(context: Context?, modelAssetPath: String): TFLiteInterpreter {
        val appContext = context ?: error("Context is required when using the default TFLite interpreter loader")
        val buffer = loadModelFile(appContext, modelAssetPath)
        val interpreter = Interpreter(buffer, Interpreter.Options())
        return AndroidTFLiteInterpreter(interpreter)
    }

    private fun loadModelFile(context: Context, assetPath: String): MappedByteBuffer {
        val fd = context.assets.openFd(assetPath)
        return fd.use {
            it.createInputStream().channel.map(
                FileChannel.MapMode.READ_ONLY,
                it.startOffset,
                it.declaredLength,
            )
        }
    }
}

private class AndroidTFLiteInterpreter(
    private val delegate: Interpreter,
) : TFLiteInterpreter {

    override val inputTensorCount: Int
        get() = delegate.inputTensorCount

    override val outputTensorCount: Int
        get() = delegate.outputTensorCount

    override fun getInputTensor(index: Int): TFLiteTensorInfo {
        val tensor = delegate.getInputTensor(index)
        return TFLiteTensorInfo(name = tensor.name(), shape = tensor.shape())
    }

    override fun getOutputTensor(index: Int): TFLiteTensorInfo {
        val tensor = delegate.getOutputTensor(index)
        return TFLiteTensorInfo(name = tensor.name(), shape = tensor.shape())
    }

    override fun run(input: FloatArray, output: Any) {
        delegate.run(input, output)
    }

    override fun runForMultipleInputsOutputs(inputs: Array<Any?>, outputs: Map<Int, Any>) {
        delegate.runForMultipleInputsOutputs(inputs, outputs)
    }
}
