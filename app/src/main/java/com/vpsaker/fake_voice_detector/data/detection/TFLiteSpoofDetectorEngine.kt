package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import android.util.Log

/**
 * TFLite inference engine.
 *
 * Supports two model architectures automatically:
 *  1. Single-input DNN  → input shape [1, N]  (N acoustic features)
 *  2. Dual-input fusion  → inputs: spec [1, T, F] + acoustic [1, N]
 *     (cross_scale_attention_lite architecture)
 *
 * Both models are detected at runtime from the TFLite graph.
 */
class TFLiteSpoofDetectorEngine(
    private val context: Context? = null,
    private val modelAssetPath: String = DEFAULT_MODEL_PATH,
    private val interpreterLoader: TFLiteInterpreterLoader = TFLiteInterpreterLoader(),
) : SpoofDetectorEngine {

    private val featureExtractor = AudioFeatureExtractor()
    private val modelTypeDetector = TFLiteModelTypeDetector()
    private val outputResolver = TFLiteOutputResolver()
    private val dualInputPreprocessor = DualInputAudioPreprocessor(featureExtractor)

    override val modelName: String
        get() = if (interpreter != null) "tflite-$modelType" else "unavailable-model"

    private val interpreter: TFLiteInterpreter? by lazy { loadInterpreter() }
    private val modelType: String get() = when (cachedModelType) {
        is TFLiteModelType.SingleInput -> "single-input"
        is TFLiteModelType.DualInput   -> "dual-input-spec+acoustic"
        null                           -> "unknown"
    }
    private var cachedModelType: TFLiteModelType? = null

    private fun loadInterpreter(): TFLiteInterpreter? = runCatching {
        val interp = interpreterLoader.load(context, modelAssetPath)
        cachedModelType = modelTypeDetector.detect(interp)
        val inputShapes = (0 until interp.inputTensorCount).joinToString(", ") { idx ->
            val tensor = interp.getInputTensor(idx)
            "#${idx}:${tensor.name}=${tensor.shape.contentToString()}"
        }
        val outputShapes = (0 until interp.outputTensorCount).joinToString(", ") { idx ->
            val tensor = interp.getOutputTensor(idx)
            "#${idx}:${tensor.name}=${tensor.shape.contentToString()}"
        }
        logInfo("Model loaded: $modelAssetPath | type=$modelType")
        logInfo("Model IO | inputs=$inputShapes | outputs=$outputShapes")
        interp
    }.getOrElse { e ->
        logError("Failed to load model: $e")
        null
    }

    // ─── Public API ──────────────────────────────────────────────────────────

    override fun detectSpoofProbability(pcm: ShortArray, sampleRateHz: Int): Float {
        val tflite = interpreter
            ?: throw IllegalStateException("Release mode requires a valid spoof detection model")

        return runCatching {
            val t0 = System.nanoTime()
            val result = when (val mt = cachedModelType) {
                is TFLiteModelType.SingleInput -> runSingleInput(tflite, pcm, sampleRateHz, mt)
                is TFLiteModelType.DualInput   -> runDualInput(tflite, pcm, sampleRateHz, mt)
                null -> throw IllegalStateException("Unable to determine deployed model input layout")
            }
            val ms = (System.nanoTime() - t0) / 1_000_000.0
            logInfo("TFLite inference: %.2f ms | score=%.4f | model=$modelType".format(ms, result))
            result.coerceIn(0f, 1f)
        }.getOrElse { e ->
            logError("Inference error: $e")
            throw IllegalStateException("TFLite inference failed in release mode", e)
        }
    }

    // ─── Single-input (DNN-8feat original) ───────────────────────────────────

    private fun runSingleInput(tflite: TFLiteInterpreter, pcm: ShortArray, sr: Int, mt: TFLiteModelType.SingleInput): Float {
        val features = featureExtractor.extractFullFeatureVector(pcm, sr)
        val inputVec = FloatArray(mt.numFeatures)
        for (i in 0 until minOf(features.size, mt.numFeatures)) inputVec[i] = features[i]
        return outputResolver.resolveFromSingleInputRun(tflite, inputVec)
    }

    // ─── Dual-input (cross_scale_attention_lite) ──────────────────────────────

    private fun runDualInput(tflite: TFLiteInterpreter, pcm: ShortArray, sr: Int, mt: TFLiteModelType.DualInput): Float {
        if (mt.specT != TARGET_SPEC_FRAMES || mt.specF != TARGET_SPEC_BINS) {
            logWarning("Unexpected spec shape: ${mt.specT}x${mt.specF}; forcing ${TARGET_SPEC_FRAMES}x${TARGET_SPEC_BINS} for deployed cross-scale model")
        }

        val spec = dualInputPreprocessor.buildSpectrogramInput(
            audioPcm = pcm,
            sampleRateHz = sr,
            targetFrames = TARGET_SPEC_FRAMES,
            targetBins = TARGET_SPEC_BINS,
        )
        val feats = dualInputPreprocessor.buildAcousticInput(pcm, sr, mt.numAcoustic)

        val outputBuffer: Any = outputResolver.createOutputBuffer(tflite)
        val output = mapOf(0 to outputBuffer)

        // Identify which tensor index is spec (3-D) vs acoustic (2-D)
        val nIn = tflite.inputTensorCount
        val specTensorIdx  = (0 until nIn).first { tflite.getInputTensor(it).shape.size == 3 }
        val acouTensorIdx  = (0 until nIn).first { tflite.getInputTensor(it).shape.size == 2 }

        val inputs = arrayOfNulls<Any>(nIn)
        inputs[specTensorIdx] = spec
        inputs[acouTensorIdx] = feats

        tflite.runForMultipleInputsOutputs(inputs, output)
        val scores = (output[0] as Array<*>)[0] as FloatArray
        val resolved = outputResolver.resolveSpoofScore(scores)
        logInfo("Dual-input raw output=${scores.joinToString(prefix = "[", postfix = "]") { "%.6f".format(it) }} resolved=%.6f".format(resolved))
        return resolved
    }

    private fun logInfo(message: String) {
        runCatching { Log.i(TAG, message) }
    }

    private fun logWarning(message: String) {
        runCatching { Log.w(TAG, message) }
    }

    private fun logError(message: String) {
        runCatching { Log.e(TAG, message) }
    }

    companion object {
        private const val DEFAULT_MODEL_PATH = "models/voice_spoof_detector.tflite"
        private const val TAG = "TFLiteSpoofEngine"
        private const val TARGET_SPEC_FRAMES = 400
        private const val TARGET_SPEC_BINS = 80
    }
}
