package com.vpsaker.fake_voice_detector.data.detection

import android.content.Context
import com.vpsaker.fake_voice_detector.data.audio.AudioRecorder
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import java.io.DataOutputStream
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import kotlin.math.abs
import kotlin.math.max

class VoiceSpoofingRepositoryImpl(
    private val recorder: AudioRecorder,
    private val featureExtractor: AudioFeatureExtractor,
    private val detectorEngine: SpoofDetectorEngine,
    private val context: Context? = null,
    private val sampleRateHz: Int = SAMPLE_RATE_HZ
) : VoiceSpoofingRepository {

    override suspend fun startRecording(): Result<Unit> {
        return recorder.start(sampleRateHz)
    }

    override suspend fun stopRecordingAndAnalyze(): Result<DetectionResult> {
        val audio = recorder.stop()
        if (audio.isEmpty()) {
            return Result.failure(IllegalStateException("No audio captured"))
        }

        return runCatching {
            val features = featureExtractor.extractFeatures(audio, sampleRateHz)
            validateAudioQuality(features)
            validateSpeechPresence(audio)
            val spoofProbability = detectorEngine.detectSpoofProbability(features)
            DetectionResult(
                spoofProbability = spoofProbability,
                modelName = detectorEngine.modelName,
                recordingDurationSec = audio.size.toFloat() / sampleRateHz.toFloat()
            )
        }
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
            val features = featureExtractor.extractFeatures(audio, sampleRateHz)
            validateAudioQuality(features)
            validateSpeechPresence(audio)

            val datasetDir = File(appContext.filesDir, "dataset_samples/$normalizedLabel").apply { mkdirs() }
            val file = File(datasetDir, "${System.currentTimeMillis()}_${audio.size}.wav")
            writeWavFile(file, audio, sampleRateHz)
            file.absolutePath
        }
    }

    override fun isRecording(): Boolean = recorder.isRecording()

    private fun validateAudioQuality(features: FloatArray) {
        val rms = features.getOrElse(0) { 0f }
        val clippingRatio = features.getOrElse(5) { 0f }
        val durationSec = features.getOrElse(7) { 0f }

        if (durationSec < MIN_DURATION_SEC) {
            throw IllegalStateException("Audio too short. Please record at least ${MIN_DURATION_SEC.toInt()} second(s).")
        }
        if (durationSec > MAX_DURATION_SEC) {
            throw IllegalStateException("Audio too long. Keep recording under ${MAX_DURATION_SEC.toInt()} seconds.")
        }
        if (rms < MIN_RMS) {
            throw IllegalStateException("Input volume is too low. Move closer to microphone and retry.")
        }
        if (clippingRatio > MAX_CLIPPING_RATIO) {
            throw IllegalStateException("Audio is clipped/noisy. Reduce volume and retry.")
        }
    }

    private fun validateSpeechPresence(audio: ShortArray) {
        val frameSize = (sampleRateHz * FRAME_SEC).toInt().coerceAtLeast(1)
        val hopSize = (sampleRateHz * HOP_SEC).toInt().coerceAtLeast(1)
        if (audio.size < frameSize) {
            throw IllegalStateException("No speech detected. Please speak clearly and retry.")
        }

        val frameEnergies = ArrayList<Float>()
        var index = 0
        while (index + frameSize <= audio.size) {
            var sumAbs = 0f
            for (i in index until index + frameSize) {
                sumAbs += abs(audio[i] / Short.MAX_VALUE.toFloat())
            }
            frameEnergies.add(sumAbs / frameSize)
            index += hopSize
        }

        if (frameEnergies.isEmpty()) {
            throw IllegalStateException("No speech detected. Please speak clearly and retry.")
        }

        val sorted = frameEnergies.sorted()
        val noiseFloor = sorted[(sorted.size * 0.2f).toInt().coerceIn(0, sorted.lastIndex)]
        val activityThreshold = max(SPEECH_ENERGY_MIN, noiseFloor * DYNAMIC_NOISE_MULTIPLIER)
        val voicedFrames = frameEnergies.count { it >= activityThreshold }
        val voicedRatio = voicedFrames.toFloat() / frameEnergies.size.toFloat()

        if (voicedFrames < MIN_VOICED_FRAMES || voicedRatio < MIN_VOICED_RATIO) {
            throw IllegalStateException("No speech detected. Please speak clearly and retry.")
        }
    }

    private fun normalizeLabel(label: String): String {
        val clean = label.trim().lowercase()
        return if (clean == "spoof") "spoof" else "bonafide"
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
        private const val MIN_DURATION_SEC = 1.0f
        private const val MAX_DURATION_SEC = 15.0f
        private const val MIN_RMS = 0.01f
        private const val MAX_CLIPPING_RATIO = 0.35f
        private const val FRAME_SEC = 0.020f
        private const val HOP_SEC = 0.010f
        private const val SPEECH_ENERGY_MIN = 0.015f
        private const val DYNAMIC_NOISE_MULTIPLIER = 2.5f
        private const val MIN_VOICED_FRAMES = 5
        private const val MIN_VOICED_RATIO = 0.20f
    }
}
