package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import android.os.Build
import android.util.Log
import com.vpsaker.fake_voice_detector.data.audio.AudioQualityGate
import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import com.vpsaker.fake_voice_detector.domain.model.AcousticFeatureSnapshot
import com.vpsaker.fake_voice_detector.domain.model.AudioInputMetadata
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import java.io.ByteArrayInputStream
import java.io.DataOutputStream
import java.io.File
import java.io.FileOutputStream
import java.io.IOException
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest

class VoiceSpoofingRepositoryImpl(
    private val recorder: AudioRecorder,
    private val featureExtractor: AudioFeatureExtractor,
    private val detectorEngine: SpoofDetectorEngine,
    private val context: Context? = null,
    private val sampleRateHz: Int = SAMPLE_RATE_HZ,
    private val skipQualityChecksOnEmulator: Boolean = true,
    private val bypassAudioValidation: Boolean = false,
) : VoiceSpoofingRepository {

    override suspend fun startRecording(): Result<Unit> {
        return recorder.start(sampleRateHz)
    }

    override suspend fun stopRecordingAndAnalyze(): Result<DetectionResult> {
        val audio = recorder.stop()
        if (audio.isEmpty()) {
            return Result.failure(IllegalStateException("No audio captured"))
        }

        return analyzeAudioSamples(
            audio = audio,
            inputSampleRateHz = sampleRateHz,
            inputMetadata = AudioInputMetadata(
                inputSource = INPUT_SOURCE_MICROPHONE,
                originalSampleRateHz = sampleRateHz,
                normalizedSampleRateHz = sampleRateHz,
                channelCount = 1,
            )
        )
    }

    override suspend fun stopRecordingAndSaveSample(label: String): Result<String> {
        val audio = recorder.stop()
        if (audio.isEmpty()) {
            return Result.failure(IllegalStateException("No audio captured"))
        }
        val appContext = context ?: return Result.failure(
            IllegalStateException("Dataset capture is unavailable in current environment")
        )

        return runCatching {
            val normalizedLabel = normalizeLabel(label)
            validateAudioInput(audio)

            val datasetDir = File(appContext.filesDir, "dataset_samples/$normalizedLabel").apply { mkdirs() }
            val file = File(datasetDir, "${System.currentTimeMillis()}_${audio.size}.wav")
            writeWavFile(file, audio, sampleRateHz)
            file.absolutePath
        }
    }

    override suspend fun analyzeImportedAudio(fileName: String, data: ByteArray): Result<DetectionResult> {
        return runCatching {
            val wav = parseWaveFile(data)
            analyzeAudioSamples(
                audio = wav.samples,
                inputSampleRateHz = wav.sampleRateHz,
                inputMetadata = AudioInputMetadata(
                    inputSource = INPUT_SOURCE_IMPORTED_FILE,
                    fileName = fileName.ifBlank { null },
                    fileHash = md5Hex(data),
                    originalSampleRateHz = wav.sampleRateHz,
                    normalizedSampleRateHz = sampleRateHz,
                    channelCount = wav.channels,
                )
            )
                .getOrThrow()
        }.recoverCatching { throwable ->
            throw IllegalStateException(
                "Khong the phan tich file ${fileName.ifBlank { "audio" }}: ${throwable.message}",
                throwable
            )
        }
    }

    override fun isRecording(): Boolean = recorder.isRecording()

    private fun validateAudioInput(audio: ShortArray) {
        if (bypassAudioValidation) {
            logDebug("Audio validation bypassed for benchmark/test execution")
            return
        }

        // Skip all duration + volume checks on emulator — virtual mic is unreliable
        if (shouldBypassAudioValidation()) {
            logDebug("Emulator detected — skipping all audio quality validation")
            return
        }

        val acousticFeatures = featureExtractor.extractAcousticFeatures(audio, sampleRateHz)
        val clippingRatio = acousticFeatures.getOrElse(AudioFeatureExtractor.CLIPPING_RATIO_INDEX) { 0f }
        val durationSec = acousticFeatures.getOrElse(AudioFeatureExtractor.DURATION_SEC_INDEX) { 0f }

        if (durationSec > MAX_DURATION_SEC) {
            throw IllegalStateException("Audio too long. Keep recording under ${MAX_DURATION_SEC.toInt()} seconds.")
        }
        if (clippingRatio > MAX_CLIPPING_RATIO) {
            throw IllegalStateException("Audio is clipped/noisy. Reduce volume and retry.")
        }

        val gate = AudioQualityGate.check(
            pcm = audio,
            sampleRateHz = sampleRateHz,
            minDurationSec = MIN_ACTIVE_SPEECH_SEC,
            minRmsdB = MIN_RMS_DBF,
            minSnrDB = MIN_SNR_DB
        )
        if (!gate.passed) {
            when {
                gate.reason.startsWith("too_quiet") ->
                    throw IllegalStateException("Input volume is too low. Move closer to microphone and retry.")
                gate.reason.startsWith("too_short") ->
                    throw IllegalStateException("No speech detected. Please speak clearly and retry.")
                gate.reason.startsWith("too_noisy") ->
                    throw IllegalStateException("Background noise is too high. Move to a quieter place and retry.")
                else ->
                    throw IllegalStateException("Audio quality is insufficient for analysis. Please retry.")
            }
        }
    }

    private fun analyzeAudioSamples(
        audio: ShortArray,
        inputSampleRateHz: Int,
        inputMetadata: AudioInputMetadata,
    ): Result<DetectionResult> {
        return runCatching {
            if (audio.isEmpty()) {
                throw IllegalStateException("No audio captured")
            }

            val normalizedAudio = if (inputSampleRateHz == sampleRateHz) {
                audio
            } else {
                resampleTo16k(audio, inputSampleRateHz)
            }

            validateAudioInput(normalizedAudio)

            val t0 = System.nanoTime()
            val acousticValues = featureExtractor.extractAcousticFeatures(normalizedAudio, sampleRateHz)
            val featureMs = (System.nanoTime() - t0) / 1_000_000L

            val t1 = System.nanoTime()
            val spoofProbability = detectorEngine.detectSpoofProbability(normalizedAudio, sampleRateHz)
            val inferenceMs = (System.nanoTime() - t1) / 1_000_000L

            logInfo("Pipeline | Feature extraction: ${featureMs}ms | TFLite inference: ${inferenceMs}ms")

            DetectionResult(
                spoofProbability = spoofProbability,
                modelName = detectorEngine.modelName,
                recordingDurationSec = normalizedAudio.size.toFloat() / sampleRateHz.toFloat(),
                featureExtractionMs = featureMs,
                inferenceMs = inferenceMs,
                inputMetadata = inputMetadata.copy(normalizedSampleRateHz = sampleRateHz),
                acousticFeatures = acousticValues.toSnapshot(),
            )
        }
    }

    private fun FloatArray.toSnapshot(): AcousticFeatureSnapshot {
        return AcousticFeatureSnapshot(
            rms = getOrElse(AudioFeatureExtractor.RMS_INDEX) { 0f },
            meanAbs = getOrElse(AudioFeatureExtractor.MEAN_ABS_INDEX) { 0f },
            zcr = getOrElse(AudioFeatureExtractor.ZCR_INDEX) { 0f },
            peak = getOrElse(AudioFeatureExtractor.PEAK_INDEX) { 0f },
            crestFactor = getOrElse(AudioFeatureExtractor.CREST_FACTOR_INDEX) { 0f },
            clippingRatio = getOrElse(AudioFeatureExtractor.CLIPPING_RATIO_INDEX) { 0f },
            dynamicRange = getOrElse(AudioFeatureExtractor.DYNAMIC_RANGE_INDEX) { 0f },
            durationSec = getOrElse(AudioFeatureExtractor.DURATION_SEC_INDEX) { 0f },
        )
    }

    private fun md5Hex(data: ByteArray): String {
        val digest = MessageDigest.getInstance("MD5").digest(data)
        return buildString(digest.size * 2) {
            digest.forEach { append("%02x".format(it)) }
        }
    }

    private fun isEmulator(): Boolean =
        Build.FINGERPRINT.startsWith("generic") ||
        Build.FINGERPRINT.startsWith("unknown") ||
        Build.MODEL.contains("Emulator", ignoreCase = true) ||
        Build.MODEL.contains("Android SDK built for", ignoreCase = true) ||
        Build.MANUFACTURER.contains("Genymotion", ignoreCase = true) ||
        Build.BRAND.startsWith("generic") ||
        Build.DEVICE.startsWith("generic") ||
        Build.PRODUCT.startsWith("sdk")

    private fun shouldBypassAudioValidation(): Boolean =
        skipQualityChecksOnEmulator && isEmulator()

    private fun logInfo(message: String) {
        runCatching { Log.i(TAG, message) }
    }

    private fun logDebug(message: String) {
        runCatching { Log.d(TAG, message) }
    }

    private fun normalizeLabel(label: String): String {
        val clean = label.trim().lowercase()
        return if (clean == "spoof") "spoof" else "bonafide"
    }

    private fun parseWaveFile(data: ByteArray): ParsedWave {
        if (data.size < WAV_HEADER_MIN_SIZE) {
            throw IOException("WAV file is too small")
        }

        val input = ByteArrayInputStream(data)
        val riff = ByteArray(4)
        val wave = ByteArray(4)
        if (input.read(riff) != 4 || String(riff) != "RIFF") {
            throw IOException("Unsupported WAV header")
        }
        input.skip(4)
        if (input.read(wave) != 4 || String(wave) != "WAVE") {
            throw IOException("Unsupported WAV format")
        }

        var channels = 1
        var sampleRate = sampleRateHz
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

        val rawData = pcmData ?: throw IOException("Missing WAV audio data")
        if (channels <= 0) throw IOException("Invalid channel count")

        val shortBuffer = ByteBuffer.wrap(rawData).order(ByteOrder.LITTLE_ENDIAN).asShortBuffer()
        val interleaved = ShortArray(shortBuffer.remaining())
        shortBuffer.get(interleaved)
        val mono = if (channels == 1) {
            interleaved
        } else {
            downmixToMono(interleaved, channels)
        }

        return ParsedWave(samples = mono, sampleRateHz = sampleRate, channels = channels)
    }

    private fun downmixToMono(interleaved: ShortArray, channels: Int): ShortArray {
        val frameCount = interleaved.size / channels
        val mono = ShortArray(frameCount)
        var frameIndex = 0
        var sampleIndex = 0
        while (frameIndex < frameCount) {
            var sum = 0
            for (channel in 0 until channels) {
                sum += interleaved[sampleIndex + channel].toInt()
            }
            mono[frameIndex] = (sum / channels).toShort()
            frameIndex++
            sampleIndex += channels
        }
        return mono
    }

    private fun resampleTo16k(source: ShortArray, sourceRateHz: Int): ShortArray {
        if (sourceRateHz <= 0) {
            throw IllegalStateException("Invalid sample rate: $sourceRateHz")
        }
        if (source.isEmpty() || sourceRateHz == sampleRateHz) return source

        val ratio = sampleRateHz.toDouble() / sourceRateHz.toDouble()
        val outputSize = (source.size * ratio).toInt().coerceAtLeast(1)
        val output = ShortArray(outputSize)
        for (i in 0 until outputSize) {
            val srcPos = i / ratio
            val left = srcPos.toInt().coerceIn(0, source.lastIndex)
            val right = (left + 1).coerceAtMost(source.lastIndex)
            val frac = (srcPos - left).toFloat()
            val interpolated = source[left] + ((source[right] - source[left]) * frac)
            output[i] = interpolated.toInt().toShort()
        }
        return output
    }

    private fun readLittleEndianInt(input: ByteArrayInputStream): Int {
        val bytes = ByteArray(4)
        if (input.read(bytes) != 4) throw IOException("Unexpected end of WAV header")
        return ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).int
    }

    private fun writeWavFile(output: File, audio: ShortArray, sampleRate: Int) {
        val channels = 1
        val bitsPerSample = 16
        val byteRate = sampleRate * channels * bitsPerSample / 8
        val dataSize = audio.size * 2
        val chunkSize = 36 + dataSize

        DataOutputStream(FileOutputStream(output)).use { out ->
            out.writeBytes("RIFF")
            out.write(leInt(chunkSize))
            out.writeBytes("WAVE")
            out.writeBytes("fmt ")
            out.write(leInt(16))
            out.write(leShort(1))
            out.write(leShort(channels))
            out.write(leInt(sampleRate))
            out.write(leInt(byteRate))
            out.write(leShort(channels * bitsPerSample / 8))
            out.write(leShort(bitsPerSample))
            out.writeBytes("data")
            out.write(leInt(dataSize))
            audio.forEach { sample ->
                out.write(leShort(sample.toInt()))
            }
        }
    }

    private fun leInt(value: Int): ByteArray =
        ByteBuffer.allocate(4).order(ByteOrder.LITTLE_ENDIAN).putInt(value).array()

    private fun leShort(value: Int): ByteArray =
        ByteBuffer.allocate(2).order(ByteOrder.LITTLE_ENDIAN).putShort(value.toShort()).array()

    companion object {
        const val SAMPLE_RATE_HZ = 16_000
        private const val INPUT_SOURCE_MICROPHONE = "microphone"
        private const val INPUT_SOURCE_IMPORTED_FILE = "imported_file"
        private const val MAX_DURATION_SEC = 15.0f
        private const val MAX_CLIPPING_RATIO = 0.35f
        private const val MIN_ACTIVE_SPEECH_SEC = 0.45f
        private const val MIN_RMS_DBF = -48f
        private const val MIN_SNR_DB = 3f
        private const val WAV_HEADER_MIN_SIZE = 44
        private const val TAG = "VoicePipeline"
    }

    private data class ParsedWave(
        val samples: ShortArray,
        val sampleRateHz: Int,
        val channels: Int,
    )
}
