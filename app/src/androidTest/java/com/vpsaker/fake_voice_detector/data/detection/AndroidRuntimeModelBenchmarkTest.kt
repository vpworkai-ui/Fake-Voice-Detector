package com.vpsaker.fake_voice_detector.data.detection

import android.util.Log
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.json.JSONObject
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import java.io.ByteArrayInputStream
import java.io.File
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.time.Instant
import java.util.Locale
import kotlin.math.abs

@RunWith(AndroidJUnit4::class)
class AndroidRuntimeModelBenchmarkTest {

    private val outputResolver = TFLiteOutputResolver()

    @Test
    fun benchmarkSelectedModelsOnDevice() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val args = InstrumentationRegistry.getArguments()
        val testContext = instrumentation.context

        val datasetRootPath = args.getString("datasetRoot")
            ?: error("Missing instrumentation arg: datasetRoot")
        val datasetRoot = File(datasetRootPath)
        require(datasetRoot.isDirectory) { "Dataset root not found on device: $datasetRootPath" }

        val threshold = args.getString("threshold")?.toFloatOrNull() ?: DEFAULT_THRESHOLD
        val progressEvery = args.getString("progressEvery")?.toIntOrNull() ?: DEFAULT_PROGRESS_EVERY
        val outputPath = args.getString("outputPath") ?: DEFAULT_OUTPUT_PATH
        val manifestPath = args.getString("manifestPath")
        val requestedModels = args.getString("models")
            ?.split(',')
            ?.map { it.trim() }
            ?.filter { it.isNotEmpty() }
            ?.toSet()
            ?: MODEL_CONFIGS.keys

        val sampleEntries = loadSamples(datasetRoot, manifestPath)
        assertTrue("No wav files found for Android runtime benchmark", sampleEntries.isNotEmpty())

        val summary = JSONObject()
            .put("generatedAt", Instant.now().toString())
            .put("datasetRoot", datasetRoot.absolutePath)
            .put("manifestPath", manifestPath ?: JSONObject.NULL)
            .put("threshold", threshold.toDouble())
            .put("sampleCount", sampleEntries.size)
            .put("models", JSONObject())

        val modelsJson = summary.getJSONObject("models")
        val runner = AndroidRuntimeModelRunner(testContext, outputResolver)

        for ((modelKey, config) in MODEL_CONFIGS) {
            if (modelKey !in requestedModels) continue
            val result = runner.benchmark(
                config = config,
                samples = sampleEntries,
                datasetRoot = datasetRoot,
                threshold = threshold,
                progressEvery = progressEvery,
            )
            modelsJson.put(modelKey, result.toJson())
        }

        val outputFile = File(outputPath)
        outputFile.parentFile?.mkdirs()
        outputFile.writeText(summary.toString(2))

        println("=== ANDROID RUNTIME MODEL BENCHMARK START ===")
        println(summary.toString(2))
        println("=== ANDROID RUNTIME MODEL BENCHMARK END ===")

        assertTrue("Expected at least one model result", modelsJson.length() > 0)
    }

    private fun loadSamples(datasetRoot: File, manifestPath: String?): List<SampleEntry> {
        if (!manifestPath.isNullOrBlank()) {
            val manifestFile = File(manifestPath)
            require(manifestFile.isFile) { "Manifest file not found on device: $manifestPath" }
            return manifestFile.readLines()
                .map { it.trim() }
                .filter { it.isNotEmpty() && !it.startsWith("#") }
                .map { line ->
                    val parts = line.split('\t')
                    require(parts.size >= 2) { "Invalid manifest line: $line" }
                    SampleEntry(relativePath = parts[0], label = parseLabel(parts[1]))
                }
        }

        return datasetRoot.walkTopDown()
            .filter { it.isFile && it.extension.equals("wav", ignoreCase = true) }
            .map { file ->
                val rel = file.relativeTo(datasetRoot).invariantSeparatorsPath
                SampleEntry(relativePath = rel, label = inferLabel(rel))
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

    private data class SampleEntry(
        val relativePath: String,
        val label: Int,
    )

    private data class ModelConfig(
        val displayName: String,
        val assetPath: String,
    )

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
    }

    private class AndroidRuntimeModelRunner(
        private val context: android.content.Context,
        private val outputResolver: TFLiteOutputResolver,
        private val featureExtractor: AudioFeatureExtractor = AudioFeatureExtractor(),
        private val dualInputPreprocessor: DualInputAudioPreprocessor = DualInputAudioPreprocessor(featureExtractor),
        private val spectrogramExtractor: LogMelSpectrogramExtractor = LogMelSpectrogramExtractor(),
        private val loader: TFLiteInterpreterLoader = TFLiteInterpreterLoader(),
    ) {

        fun benchmark(
            config: ModelConfig,
            samples: List<SampleEntry>,
            datasetRoot: File,
            threshold: Float,
            progressEvery: Int,
        ): ModelResult {
            val interpreter = loader.load(context, config.assetPath)
            val inputTensors = (0 until interpreter.inputTensorCount).map { interpreter.getInputTensor(it) }
            val outputBuffer = outputResolver.createOutputBuffer(interpreter)
            val modelMd5 = context.assets.open(config.assetPath).use { stream ->
                java.security.MessageDigest.getInstance("MD5")
                    .digest(stream.readBytes())
                    .joinToString("") { "%02x".format(it) }
            }

            val rows = ArrayList<ScoreRow>(samples.size)
            var featureMsTotal = 0L
            var inferenceMsTotal = 0L
            var totalMsTotal = 0L

            for ((index, sample) in samples.withIndex()) {
                val file = File(datasetRoot, sample.relativePath)
                require(file.isFile) { "Missing dataset file on device: ${file.absolutePath}" }
                val bytes = file.readBytes()
                val wav = parseWave(bytes)
                val mono16k = if (wav.sampleRateHz == SAMPLE_RATE_HZ) wav.samples else resampleTo16k(wav.samples, wav.sampleRateHz)

                val t0 = System.nanoTime()
                val prepared = prepareInput(interpreter, inputTensors, mono16k)
                val featureMs = nanosToMillis(System.nanoTime() - t0)

                val t1 = System.nanoTime()
                val rawScore = runInference(interpreter, inputTensors, outputBuffer, prepared)
                val inferenceMs = nanosToMillis(System.nanoTime() - t1)
                val totalMs = nanosToMillis(System.nanoTime() - t0)

                featureMsTotal += featureMs
                inferenceMsTotal += inferenceMs
                totalMsTotal += totalMs
                rows += ScoreRow(score = rawScore, label = sample.label)

                if ((index + 1) % progressEvery == 0 || index == samples.lastIndex) {
                    Log.i(TAG, "${config.displayName}: processed ${index + 1}/${samples.size}")
                }
            }

            val metrics = evaluate(rows, threshold)
            return ModelResult(
                modelKey = MODEL_CONFIGS.entries.first { it.value == config }.key,
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
                averageFeatureMs = featureMsTotal.toDouble() / rows.size.toDouble(),
                averageInferenceMs = inferenceMsTotal.toDouble() / rows.size.toDouble(),
                averageTotalMs = totalMsTotal.toDouble() / rows.size.toDouble(),
                md5 = modelMd5,
            )
        }

        private fun prepareInput(
            interpreter: TFLiteInterpreter,
            inputTensors: List<TFLiteTensorInfo>,
            audioPcm: ShortArray,
        ): PreparedInput {
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
                require(specIndex >= 0 && acousticIndex >= 0) { "Unsupported dual-input layout: $inputTensors" }
                val specShape = inputTensors[specIndex].shape
                val acousticShape = inputTensors[acousticIndex].shape
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
                val acousticInput = arrayOf(FloatArray(acousticShape[1]).also { dst ->
                    for (index in 0 until minOf(dst.size, acoustic.size)) dst[index] = acoustic[index]
                })
                return PreparedInput.Multi(
                    inputs = arrayOfNulls<Any>(inputTensors.size).also { arr ->
                        arr[specIndex] = spec
                        arr[acousticIndex] = acousticInput
                    }
                )
            }

            val shape = inputTensors.single().shape
            return when (shape.size) {
                2 -> {
                    val cols = shape[1]
                    if (cols == 80) {
                        PreparedInput.Multi(arrayOf(arrayOf(spec400x80[0][0])))
                    } else {
                        PreparedInput.Single(
                            FloatArray(cols).also { dst ->
                                for (index in 0 until minOf(dst.size, fullFeature.size)) dst[index] = fullFeature[index]
                            }
                        )
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
                else -> error("Unsupported single-input shape: ${shape.contentToString()}")
            }
        }

        private fun runInference(
            interpreter: TFLiteInterpreter,
            inputTensors: List<TFLiteTensorInfo>,
            outputBuffer: Any,
            prepared: PreparedInput,
        ): Float {
            return when (prepared) {
                is PreparedInput.Single -> outputResolver.resolveFromSingleInputRun(interpreter, prepared.vector)
                is PreparedInput.Multi -> {
                    interpreter.runForMultipleInputsOutputs(prepared.inputs, mapOf(0 to outputBuffer))
                    val raw = when (outputBuffer) {
                        is Array<*> -> outputBuffer[0] as FloatArray
                        else -> error("Unexpected output buffer: ${outputBuffer::class.java.simpleName}")
                    }
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

            val total = rows.size.toDouble()
            val precision = safeDivide(tp.toDouble(), (tp + fp).toDouble())
            val recall = safeDivide(tp.toDouble(), (tp + fn).toDouble())
            val f1 = if (precision + recall > 0) 2.0 * precision * recall / (precision + recall) else 0.0
            val far = safeDivide(fp.toDouble(), (fp + tn).toDouble())
            val frr = safeDivide(fn.toDouble(), (fn + tp).toDouble())
            val accuracy = safeDivide((tp + tn).toDouble(), total)
            val roc = computeRoc(rows)

            return Metrics(
                tp = tp,
                fp = fp,
                fn = fn,
                tn = tn,
                accuracy = accuracy,
                precision = precision,
                recall = recall,
                f1 = f1,
                far = far,
                frr = frr,
                auc = roc.auc,
                eer = roc.eer,
            )
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
            var bestEer = 1.0
            var bestGap = Double.MAX_VALUE
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

            return RocStats(auc = auc.coerceIn(0.0, 1.0), eer = bestEer.coerceIn(0.0, 1.0))
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
            var bitsPerSample = 16
            var pcmData: ByteArray? = null

            while (input.available() >= 8) {
                val chunkId = ByteArray(4)
                input.read(chunkId)
                val chunkSize = readLittleEndianInt(input)
                val chunkBytes = ByteArray(chunkSize)
                val bytesRead = input.read(chunkBytes)
                if (bytesRead != chunkSize) break
                when (String(chunkId)) {
                    "fmt " -> {
                        val fmtBuffer = ByteBuffer.wrap(chunkBytes).order(ByteOrder.LITTLE_ENDIAN)
                        val audioFormat = fmtBuffer.short.toInt() and 0xFFFF
                        channels = fmtBuffer.short.toInt() and 0xFFFF
                        sampleRate = fmtBuffer.int
                        fmtBuffer.int
                        fmtBuffer.short
                        bitsPerSample = fmtBuffer.short.toInt() and 0xFFFF
                        if (audioFormat != 1 || bitsPerSample != 16) {
                            throw IOException("Only PCM 16-bit WAV files are supported")
                        }
                    }
                    "data" -> pcmData = chunkBytes
                }
            }

            val rawData = pcmData ?: throw IOException("Missing WAV data chunk")
            val shortBuffer = ByteBuffer.wrap(rawData).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
            val interleaved = ShortArray(shortBuffer.remaining())
            shortBuffer.get(interleaved)
            val mono = if (channels == 1) interleaved else downmixToMono(interleaved, channels)
            return ParsedWave(samples = mono, sampleRateHz = sampleRate)
        }

        private fun readLittleEndianInt(input: ByteArrayInputStream): Int {
            val buffer = ByteArray(4)
            if (input.read(buffer) != 4) throw IOException("Unexpected end of stream")
            return ByteBuffer.wrap(buffer).order(ByteOrder.LITTLE_ENDIAN).int
        }

        private fun downmixToMono(interleaved: ShortArray, channels: Int): ShortArray {
            val frameCount = interleaved.size / channels
            val mono = ShortArray(frameCount)
            for (frame in 0 until frameCount) {
                var sum = 0
                for (channel in 0 until channels) {
                    sum += interleaved[frame * channels + channel].toInt()
                }
                mono[frame] = (sum / channels).toShort()
            }
            return mono
        }

        private fun resampleTo16k(input: ShortArray, sourceRateHz: Int): ShortArray {
            if (sourceRateHz == SAMPLE_RATE_HZ || input.isEmpty()) return input
            val targetSize = (input.size.toLong() * SAMPLE_RATE_HZ / sourceRateHz).toInt().coerceAtLeast(1)
            val output = ShortArray(targetSize)
            val scale = input.size.toDouble() / targetSize.toDouble()
            for (index in 0 until targetSize) {
                val src = index * scale
                val left = src.toInt().coerceIn(0, input.lastIndex)
                val right = (left + 1).coerceAtMost(input.lastIndex)
                val frac = src - left
                output[index] = ((1.0 - frac) * input[left] + frac * input[right]).toInt().toShort()
            }
            return output
        }

        private fun safeDivide(numerator: Double, denominator: Double): Double {
            return if (denominator == 0.0) 0.0 else numerator / denominator
        }

        private fun nanosToMillis(durationNs: Long): Long = durationNs / 1_000_000L

        private sealed interface PreparedInput {
            data class Single(val vector: FloatArray) : PreparedInput
            data class Multi(val inputs: Array<Any?>) : PreparedInput
        }

        private data class ParsedWave(
            val samples: ShortArray,
            val sampleRateHz: Int,
        )

        private data class ScoreRow(
            val score: Float,
            val label: Int,
        )

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

        private data class RocStats(
            val auc: Double,
            val eer: Double,
        )
    }

    companion object {
        private const val TAG = "AndroidModelBenchmark"
        private const val SAMPLE_RATE_HZ = 16_000
        private const val MAX_AUDIO_SECONDS = 4
        private const val DEFAULT_THRESHOLD = 0.25f
        private const val DEFAULT_PROGRESS_EVERY = 100
        private const val DEFAULT_OUTPUT_PATH = "/sdcard/Download/fake_voice_detector/android_runtime_benchmark.json"

        private val MODEL_CONFIGS = linkedMapOf(
            "cross_scale_attention_lite" to ModelConfig(
                displayName = "Cross-Scale Attention Lite",
                assetPath = "cross_scale_attention_lite.tflite",
            ),
            "aasist_lite" to ModelConfig(
                displayName = "AASIST Lite",
                assetPath = "aasist_lite.tflite",
            ),
            "cbam_resnet_lite" to ModelConfig(
                displayName = "CBAM-ResNet Lite",
                assetPath = "cbam_resnet_lite.tflite",
            ),
        )
    }
}
