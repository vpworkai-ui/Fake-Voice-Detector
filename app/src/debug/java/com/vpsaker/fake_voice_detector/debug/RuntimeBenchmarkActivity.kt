package com.vpsaker.fake_voice_detector.debug

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.lifecycle.lifecycleScope
import com.vpsaker.fake_voice_detector.data.detection.AudioFeatureExtractor
import com.vpsaker.fake_voice_detector.data.detection.LogMelSpectrogramExtractor
import com.vpsaker.fake_voice_detector.data.detection.TFLiteInterpreter
import com.vpsaker.fake_voice_detector.data.detection.TFLiteInterpreterLoader
import com.vpsaker.fake_voice_detector.data.detection.TFLiteOutputResolver
import com.vpsaker.fake_voice_detector.data.detection.TFLiteTensorInfo
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.time.Instant
import java.util.Locale
import kotlin.math.abs
import kotlin.math.min

class RuntimeBenchmarkActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        lifecycleScope.launch {
            val result = runCatching {
                withContext(Dispatchers.Default) {
                    runBenchmark()
                }
            }

            result.onSuccess {
                Log.i(TAG, "Runtime benchmark completed: ${it.absolutePath}")
            }.onFailure { error ->
                Log.e(TAG, "Runtime benchmark failed", error)
            }

            finish()
        }
    }

    private fun runBenchmark(): File {
        val datasetRootPath = intent.getStringExtra(EXTRA_DATASET_ROOT)
            ?: error("Missing intent extra: $EXTRA_DATASET_ROOT")
        val datasetRoot = File(datasetRootPath)
        require(datasetRoot.isDirectory) { "Dataset root not found: $datasetRootPath" }

        val manifestPath = intent.getStringExtra(EXTRA_MANIFEST_PATH)
        val outputPath = intent.getStringExtra(EXTRA_OUTPUT_PATH) ?: DEFAULT_OUTPUT_PATH
        val threshold = intent.getStringExtra(EXTRA_THRESHOLD)?.toFloatOrNull() ?: DEFAULT_THRESHOLD
        val progressEvery = intent.getStringExtra(EXTRA_PROGRESS_EVERY)?.toIntOrNull() ?: DEFAULT_PROGRESS_EVERY
        val requestedModels = intent.getStringExtra(EXTRA_MODELS)
            ?.split(',')
            ?.map { it.trim() }
            ?.filter { it.isNotEmpty() }
            ?.toSet()
            ?: MODEL_CONFIGS.keys

        val sampleEntries = loadSamples(datasetRoot, manifestPath)
        require(sampleEntries.isNotEmpty()) { "No wav files found under $datasetRootPath" }

        val summary = JSONObject()
            .put("generatedAt", Instant.now().toString())
            .put("datasetRoot", datasetRoot.absolutePath)
            .put("manifestPath", manifestPath ?: JSONObject.NULL)
            .put("threshold", threshold.toDouble())
            .put("sampleCount", sampleEntries.size)
            .put("models", JSONObject())

        val modelsJson = summary.getJSONObject("models")
        val runner = RuntimeModelRunner(applicationContext, TFLiteOutputResolver())

        for ((modelKey, config) in MODEL_CONFIGS) {
            if (modelKey !in requestedModels) continue
            val modelResult = runner.benchmark(
                modelKey = modelKey,
                config = config,
                samples = sampleEntries,
                datasetRoot = datasetRoot,
                threshold = threshold,
                progressEvery = progressEvery,
            )
            modelsJson.put(modelKey, modelResult.toJson())
        }

        val outputFile = File(outputPath)
        outputFile.parentFile?.mkdirs()
        outputFile.writeText(summary.toString(2))

        Log.i(TAG, "=== RUNTIME BENCHMARK RESULT START ===\n${summary.toString(2)}\n=== RUNTIME BENCHMARK RESULT END ===")
        return outputFile
    }

    private fun loadSamples(datasetRoot: File, manifestPath: String?): List<SampleEntry> {
        if (!manifestPath.isNullOrBlank()) {
            val manifestFile = File(manifestPath)
            require(manifestFile.isFile) { "Manifest file not found: $manifestPath" }
            return manifestFile.readLines()
                .map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("#") }
                .map { line ->
                    val parts = line.split('\t')
                    require(parts.size >= 2) { "Invalid manifest line: $line" }
                    SampleEntry(parts[0], parseLabel(parts[1]))
                }
        }

        return datasetRoot.walkTopDown()
            .filter { it.isFile && it.extension.equals("wav", ignoreCase = true) }
            .map { file ->
                val relativePath = file.relativeTo(datasetRoot).invariantSeparatorsPath
                SampleEntry(relativePath, inferLabel(relativePath))
            }
            .sortedBy { it.relativePath }
            .toList()
    }

    private fun parseLabel(value: String): Int = when (value.trim().lowercase(Locale.US)) {
        "1", "spoof" -> 1
        "0", "bonafide", "bona_fide", "real" -> 0
        else -> error("Unsupported label: $value")
    }

    private fun inferLabel(relativePath: String): Int {
        val lower = relativePath.lowercase(Locale.US)
        return when {
            "/spoof/" in "/$lower/" || lower.startsWith("spoof/") -> 1
            "/bonafide/" in "/$lower/" || lower.startsWith("bonafide/") -> 0
            else -> error("Unable to infer label from path: $relativePath")
        }
    }

    private data class SampleEntry(val relativePath: String, val label: Int)

    private data class ModelConfig(val displayName: String, val assetPath: String)

    private data class ModelResult(
        val modelKey: String,
        val displayName: String,
        val assetPath: String,
        val threshold: Float,
        val sampleCount: Int,
        val tp: Int,
        val fp: Int,
        val fn: Int,
        val tn: Int,
        val accuracy: Double,
        val precision: Double,
        val recall: Double,
        val f1: Double,
        val far: Double,
        val frr: Double,
        val auc: Double,
        val eer: Double,
        val averageFeatureMs: Double,
        val averageInferenceMs: Double,
        val averageTotalMs: Double,
        val md5: String,
        val scores: List<ScoreRecord>,
    ) {
        fun toJson(): JSONObject = JSONObject()
            .put("modelKey", modelKey)
            .put("displayName", displayName)
            .put("assetPath", assetPath)
            .put("threshold", threshold.toDouble())
            .put("sampleCount", sampleCount)
            .put("tp", tp)
            .put("fp", fp)
            .put("fn", fn)
            .put("tn", tn)
            .put("accuracy", accuracy)
            .put("precision", precision)
            .put("recall", recall)
            .put("f1", f1)
            .put("far", far)
            .put("frr", frr)
            .put("auc", auc)
            .put("eer", eer)
            .put("averageFeatureMs", averageFeatureMs)
            .put("averageInferenceMs", averageInferenceMs)
            .put("averageTotalMs", averageTotalMs)
            .put("md5", md5)
            .put("scores", org.json.JSONArray().apply {
                scores.forEach { put(it.toJson()) }
            })
    }

    private data class ScoreRecord(
        val relativePath: String,
        val label: Int,
        val score: Float,
    ) {
        fun toJson(): JSONObject = JSONObject()
            .put("relativePath", relativePath)
            .put("label", label)
            .put("score", score.toDouble())
    }

    private class RuntimeModelRunner(
        private val context: android.content.Context,
        private val outputResolver: TFLiteOutputResolver,
        private val featureExtractor: AudioFeatureExtractor = AudioFeatureExtractor(),
        private val spectrogramExtractor: LogMelSpectrogramExtractor = LogMelSpectrogramExtractor(),
        private val loader: TFLiteInterpreterLoader = TFLiteInterpreterLoader(),
    ) {

        fun benchmark(
            modelKey: String,
            config: ModelConfig,
            samples: List<SampleEntry>,
            datasetRoot: File,
            threshold: Float,
            progressEvery: Int,
        ): ModelResult {
            val interpreter = loader.load(context, config.assetPath)
            val inputTensors = (0 until interpreter.inputTensorCount).map(interpreter::getInputTensor)
            val outputBuffer = outputResolver.createOutputBuffer(interpreter)
            val md5 = context.assets.open(config.assetPath).use { stream ->
                MessageDigest.getInstance("MD5").digest(stream.readBytes()).joinToString("") { "%02x".format(it) }
            }

            val rows = ArrayList<ScoreRow>(samples.size)
            var featureMsTotal = 0L
            var inferenceMsTotal = 0L
            var totalMsTotal = 0L

            for ((index, sample) in samples.withIndex()) {
                val wav = parseWave(File(datasetRoot, sample.relativePath).readBytes())
                val mono16k = if (wav.sampleRateHz == SAMPLE_RATE_HZ) wav.samples else resampleTo16k(wav.samples, wav.sampleRateHz)

                val t0 = System.nanoTime()
                val prepared = prepareInput(inputTensors, mono16k)
                val featureMs = nanosToMillis(System.nanoTime() - t0)

                val t1 = System.nanoTime()
                val score = runInference(interpreter, outputBuffer, prepared)
                val inferenceMs = nanosToMillis(System.nanoTime() - t1)
                val totalMs = nanosToMillis(System.nanoTime() - t0)

                featureMsTotal += featureMs
                inferenceMsTotal += inferenceMs
                totalMsTotal += totalMs
                rows += ScoreRow(sample.relativePath, score, sample.label)

                if ((index + 1) % progressEvery == 0 || index == samples.lastIndex) {
                    Log.i(TAG, "${config.displayName}: processed ${index + 1}/${samples.size}")
                }
            }

            val metrics = evaluate(rows, threshold)
            return ModelResult(
                modelKey = modelKey,
                displayName = config.displayName,
                assetPath = config.assetPath,
                threshold = threshold,
                sampleCount = rows.size,
                tp = metrics.tp,
                fp = metrics.fp,
                fn = metrics.fn,
                tn = metrics.tn,
                accuracy = metrics.accuracy,
                precision = metrics.precision,
                recall = metrics.recall,
                f1 = metrics.f1,
                far = metrics.far,
                frr = metrics.frr,
                auc = metrics.auc,
                eer = metrics.eer,
                averageFeatureMs = featureMsTotal.toDouble() / rows.size,
                averageInferenceMs = inferenceMsTotal.toDouble() / rows.size,
                averageTotalMs = totalMsTotal.toDouble() / rows.size,
                md5 = md5,
                scores = rows.map { ScoreRecord(it.relativePath, it.label, it.score) },
            )
        }

        private fun prepareInput(inputTensors: List<TFLiteTensorInfo>, audioPcm: ShortArray): PreparedInput {
            val acoustic = featureExtractor.extractAcousticFeatures(
                audioPcm,
                SAMPLE_RATE_HZ,
                targetSampleCount = SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS,
            )
            val fullFeature = featureExtractor.extractFullFeatureVector(audioPcm, SAMPLE_RATE_HZ)
            val spec400x80 = spectrogramExtractor.extract(
                audioPcm = audioPcm,
                sampleRateHz = SAMPLE_RATE_HZ,
                targetSampleCount = SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS,
                targetFrames = 400,
                targetBins = 80,
            )

            if (inputTensors.size == 2) {
                val specIndex = inputTensors.indexOfFirst { it.shape.size == 3 }
                val acousticIndex = inputTensors.indexOfFirst { it.shape.size == 2 }
                require(specIndex >= 0 && acousticIndex >= 0) { "Unsupported dual-input layout" }
                val specShape = inputTensors[specIndex].shape
                val acousticInput = arrayOf(FloatArray(inputTensors[acousticIndex].shape[1]).also { dst ->
                    for (i in 0 until min(dst.size, acoustic.size)) dst[i] = acoustic[i]
                })
                val spec = if (specShape[1] == 400 && specShape[2] == 80) {
                    spec400x80
                } else {
                    spectrogramExtractor.extract(
                        audioPcm = audioPcm,
                        sampleRateHz = SAMPLE_RATE_HZ,
                        targetSampleCount = SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS,
                        targetFrames = specShape[1],
                        targetBins = specShape[2],
                    )
                }
                return PreparedInput.Multi(arrayOfNulls<Any>(inputTensors.size).also { arr ->
                    arr[specIndex] = spec
                    arr[acousticIndex] = acousticInput
                })
            }

            val shape = inputTensors.single().shape
            return when (shape.size) {
                2 -> {
                    if (shape[1] == 80) {
                        PreparedInput.Multi(arrayOf(arrayOf(spec400x80[0][0])))
                    } else {
                        PreparedInput.Single(FloatArray(shape[1]).also { dst ->
                            for (i in 0 until min(dst.size, fullFeature.size)) dst[i] = fullFeature[i]
                        })
                    }
                }
                3 -> {
                    val spec = spectrogramExtractor.extract(
                        audioPcm = audioPcm,
                        sampleRateHz = SAMPLE_RATE_HZ,
                        targetSampleCount = SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS,
                        targetFrames = shape[1],
                        targetBins = shape[2],
                    )
                    PreparedInput.Multi(arrayOf(spec))
                }
                4 -> {
                    val spec = spectrogramExtractor.extract(
                        audioPcm = audioPcm,
                        sampleRateHz = SAMPLE_RATE_HZ,
                        targetSampleCount = SAMPLE_RATE_HZ * MAX_AUDIO_SECONDS,
                        targetFrames = shape[1],
                        targetBins = shape[2],
                    )
                    val image = Array(1) { Array(shape[1]) { frame -> Array(shape[2]) { bin -> floatArrayOf(spec[0][frame][bin]) } } }
                    PreparedInput.Multi(arrayOf(image))
                }
                else -> error("Unsupported input shape: ${shape.contentToString()}")
            }
        }

        private fun runInference(
            interpreter: TFLiteInterpreter,
            outputBuffer: Any,
            prepared: PreparedInput,
        ): Float {
            return when (prepared) {
                is PreparedInput.Single -> outputResolver.resolveFromSingleInputRun(interpreter, prepared.vector)
                is PreparedInput.Multi -> {
                    interpreter.runForMultipleInputsOutputs(prepared.inputs, mapOf(0 to outputBuffer))
                    val raw = (outputBuffer as Array<*>)[0] as FloatArray
                    outputResolver.resolveSpoofScore(raw)
                }
            }
        }

        private fun evaluate(rows: List<ScoreRow>, threshold: Float): Metrics {
            var tp = 0
            var fp = 0
            var fn = 0
            var tn = 0
            for (row in rows) {
                val predicted = if (row.score >= threshold) 1 else 0
                when {
                    predicted == 1 && row.label == 1 -> tp++
                    predicted == 1 && row.label == 0 -> fp++
                    predicted == 0 && row.label == 1 -> fn++
                    else -> tn++
                }
            }
            val precision = safeDivide(tp.toDouble(), (tp + fp).toDouble())
            val recall = safeDivide(tp.toDouble(), (tp + fn).toDouble())
            val f1 = if (precision + recall > 0.0) 2.0 * precision * recall / (precision + recall) else 0.0
            val far = safeDivide(fp.toDouble(), (fp + tn).toDouble())
            val frr = safeDivide(fn.toDouble(), (fn + tp).toDouble())
            val accuracy = safeDivide((tp + tn).toDouble(), rows.size.toDouble())
            val roc = computeRoc(rows)
            return Metrics(tp, fp, fn, tn, accuracy, precision, recall, f1, far, frr, roc.auc, roc.eer)
        }

        private fun computeRoc(rows: List<ScoreRow>): RocStats {
            val sorted = rows.sortedByDescending { it.score }
            val positives = rows.count { it.label == 1 }.toDouble()
            val negatives = rows.count { it.label == 0 }.toDouble()
            var tp = 0.0
            var fp = 0.0
            var prevFpr = 0.0
            var prevTpr = 0.0
            var auc = 0.0
            var bestGap = Double.MAX_VALUE
            var bestEer = 1.0
            var index = 0
            while (index < sorted.size) {
                val score = sorted[index].score
                while (index < sorted.size && sorted[index].score == score) {
                    if (sorted[index].label == 1) tp++ else fp++
                    index++
                }
                val tpr = safeDivide(tp, positives)
                val fpr = safeDivide(fp, negatives)
                auc += (fpr - prevFpr) * (tpr + prevTpr) / 2.0
                prevFpr = fpr
                prevTpr = tpr
                val fnr = 1.0 - tpr
                val gap = abs(fpr - fnr)
                if (gap < bestGap) {
                    bestGap = gap
                    bestEer = (fpr + fnr) / 2.0
                }
            }
            return RocStats(auc.coerceIn(0.0, 1.0), bestEer.coerceIn(0.0, 1.0))
        }

        private fun parseWave(data: ByteArray): ParsedWave {
            if (data.size < 44) throw IOException("WAV file is too small")
            val input = ByteArrayInputStream(data)
            val riff = ByteArray(4)
            val wave = ByteArray(4)
            if (input.read(riff) != 4 || String(riff) != "RIFF") throw IOException("Unsupported WAV header")
            input.skip(4)
            if (input.read(wave) != 4 || String(wave) != "WAVE") throw IOException("Unsupported WAV format")
            var channels = 1
            var sampleRate = SAMPLE_RATE_HZ
            var pcmData: ByteArray? = null
            while (input.available() >= 8) {
                val chunkId = ByteArray(4)
                input.read(chunkId)
                val chunkSize = readLittleEndianInt(input)
                val chunkBytes = ByteArray(chunkSize)
                if (input.read(chunkBytes) != chunkSize) break
                when (String(chunkId)) {
                    "fmt " -> {
                        val fmt = ByteBuffer.wrap(chunkBytes).order(ByteOrder.LITTLE_ENDIAN)
                        val audioFormat = fmt.short.toInt() and 0xFFFF
                        channels = fmt.short.toInt() and 0xFFFF
                        sampleRate = fmt.int
                        fmt.int
                        fmt.short
                        val bitsPerSample = fmt.short.toInt() and 0xFFFF
                        if (audioFormat != 1 || bitsPerSample != 16) throw IOException("Only PCM 16-bit WAV files are supported")
                    }
                    "data" -> pcmData = chunkBytes
                }
            }
            val raw = pcmData ?: throw IOException("Missing WAV data chunk")
            val shortBuffer = ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
            val interleaved = ShortArray(shortBuffer.remaining())
            shortBuffer.get(interleaved)
            val mono = if (channels == 1) interleaved else downmixToMono(interleaved, channels)
            return ParsedWave(mono, sampleRate)
        }

        private fun readLittleEndianInt(input: ByteArrayInputStream): Int {
            val bytes = ByteArray(4)
            if (input.read(bytes) != 4) throw IOException("Unexpected end of stream")
            return ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).int
        }

        private fun downmixToMono(interleaved: ShortArray, channels: Int): ShortArray {
            val frameCount = interleaved.size / channels
            return ShortArray(frameCount) { frame ->
                var sum = 0
                for (channel in 0 until channels) sum += interleaved[frame * channels + channel].toInt()
                (sum / channels).toShort()
            }
        }

        private fun resampleTo16k(input: ShortArray, sourceRateHz: Int): ShortArray {
            if (sourceRateHz == SAMPLE_RATE_HZ || input.isEmpty()) return input
            val targetSize = (input.size.toLong() * SAMPLE_RATE_HZ / sourceRateHz).toInt().coerceAtLeast(1)
            return ShortArray(targetSize) { index ->
                val src = index * (input.size.toDouble() / targetSize.toDouble())
                val left = src.toInt().coerceIn(0, input.lastIndex)
                val right = (left + 1).coerceAtMost(input.lastIndex)
                val frac = src - left
                ((1.0 - frac) * input[left] + frac * input[right]).toInt().toShort()
            }
        }

        private fun safeDivide(numerator: Double, denominator: Double): Double {
            return if (denominator == 0.0) 0.0 else numerator / denominator
        }

        private fun nanosToMillis(durationNs: Long): Long = durationNs / 1_000_000L

        private sealed interface PreparedInput {
            data class Single(val vector: FloatArray) : PreparedInput
            data class Multi(val inputs: Array<Any?>) : PreparedInput
        }

        private data class ParsedWave(val samples: ShortArray, val sampleRateHz: Int)
        private data class ScoreRow(val relativePath: String, val score: Float, val label: Int)
        private data class Metrics(
            val tp: Int,
            val fp: Int,
            val fn: Int,
            val tn: Int,
            val accuracy: Double,
            val precision: Double,
            val recall: Double,
            val f1: Double,
            val far: Double,
            val frr: Double,
            val auc: Double,
            val eer: Double,
        )
        private data class RocStats(val auc: Double, val eer: Double)
    }

    companion object {
        private const val TAG = "RuntimeBenchmark"
        private const val SAMPLE_RATE_HZ = 16_000
        private const val MAX_AUDIO_SECONDS = 4
        private const val DEFAULT_THRESHOLD = 0.25f
        private const val DEFAULT_PROGRESS_EVERY = 100
        private const val DEFAULT_OUTPUT_PATH = "/sdcard/Android/media/com.vpsaker.fake_voice_detector/benchmark/android_runtime_benchmark.json"

        const val EXTRA_DATASET_ROOT = "datasetRoot"
        const val EXTRA_MANIFEST_PATH = "manifestPath"
        const val EXTRA_OUTPUT_PATH = "outputPath"
        const val EXTRA_THRESHOLD = "threshold"
        const val EXTRA_PROGRESS_EVERY = "progressEvery"
        const val EXTRA_MODELS = "models"

        private val MODEL_CONFIGS = linkedMapOf(
            "cross_scale_attention_lite" to ModelConfig("Cross-Scale Attention Lite", "cross_scale_attention_lite.tflite"),
            "aasist_lite" to ModelConfig("AASIST Lite", "aasist_lite.tflite"),
            "cbam_resnet_lite" to ModelConfig("CBAM-ResNet Lite", "cbam_resnet_lite.tflite"),
        )
    }
}
