package com.vpsaker.fake_voice_detector.data.telemetry

import android.content.Context
import android.util.Log
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.repository.TelemetryRepository
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class FileTelemetryRepository(
    private val context: Context,
    private val apiKey: String = ""
) : TelemetryRepository {

    override suspend fun logAuthenticationEvent(event: AuthTelemetryEvent): Result<Unit> {
        return runCatching {
            val directory = telemetryDirectory()
            val payloadLine = serialize(event)
            File(directory, TELEMETRY_LOG_FILE).appendText(payloadLine + "\n")
            File(directory, TELEMETRY_PENDING_FILE).appendText(payloadLine + "\n")
            Log.i(STRUCTURED_TELEMETRY_TAG, payloadLine)
        }
    }

    override suspend fun flushPendingEvents(endpoint: String): Result<Int> {
        return runCatching {
            require(endpoint.isNotBlank()) { "Telemetry endpoint is empty" }
            val pendingFile = File(telemetryDirectory(), TELEMETRY_PENDING_FILE)
            if (!pendingFile.exists()) {
                return@runCatching 0
            }

            val lines = pendingFile.readLines().filter { it.isNotBlank() }
            if (lines.isEmpty()) {
                pendingFile.writeText("")
                return@runCatching 0
            }

            val remaining = ArrayList<String>()
            var flushedCount = 0
            lines.forEach { line ->
                val success = postTelemetry(endpoint, line)
                if (success) {
                    flushedCount++
                } else {
                    remaining.add(line)
                }
            }

            pendingFile.writeText(
                if (remaining.isEmpty()) "" else remaining.joinToString(separator = "\n", postfix = "\n")
            )
            flushedCount
        }
    }

    private fun postTelemetry(endpoint: String, payloadLine: String): Boolean {
        return runCatching {
            val normalizedPayload = JSONObject(payloadLine).toString()
            val connection = (URL(endpoint).openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                connectTimeout = CONNECT_TIMEOUT_MS
                readTimeout = READ_TIMEOUT_MS
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
                setRequestProperty("Accept", "application/json")
                if (apiKey.isNotBlank()) {
                    setRequestProperty("Authorization", "Bearer $apiKey")
                    setRequestProperty("X-Api-Key", apiKey)
                }
            }

            connection.outputStream.bufferedWriter().use { writer ->
                writer.write(normalizedPayload)
                writer.flush()
            }

            connection.responseCode in 200..299
        }.getOrDefault(false)
    }

    private fun serialize(event: AuthTelemetryEvent): String {
        return JSONObject().apply {
            put("timestampMs", event.timestampMs)
            put("fileName", event.fileName)
            put("inputSource", event.inputSource)
            put("fileHash", event.fileHash)
            put("sampleRateHz", event.sampleRateHz)
            put("originalSampleRateHz", event.originalSampleRateHz)
            put("channelCount", event.channelCount)
            put("spoofProbability", event.spoofProbability)
            put("threshold", event.threshold)
            put("predictedLabel", event.predictedLabel)
            put("decision", event.decision)
            put("reason", event.reason)
            put("modelName", event.modelName)
            put("recordingDurationSec", event.recordingDurationSec)
            put("confidence", event.confidence)
            put("meetsSpoofThreshold", event.meetsSpoofThreshold)
            put("featureExtractionMs", event.featureExtractionMs)
            put("inferenceMs", event.inferenceMs)
            put("acousticFeatures", JSONObject().apply {
                put("rms", event.acousticFeatures.rms)
                put("meanAbs", event.acousticFeatures.meanAbs)
                put("zcr", event.acousticFeatures.zcr)
                put("peak", event.acousticFeatures.peak)
                put("crestFactor", event.acousticFeatures.crestFactor)
                put("clippingRatio", event.acousticFeatures.clippingRatio)
                put("dynamicRange", event.acousticFeatures.dynamicRange)
                put("durationSec", event.acousticFeatures.durationSec)
            })
        }.toString()
    }

    private fun telemetryDirectory(): File {
        return File(context.filesDir, TELEMETRY_DIR).apply { mkdirs() }
    }

    private companion object {
        const val TELEMETRY_DIR = "telemetry"
        const val TELEMETRY_LOG_FILE = "voice_auth_events.jsonl"
        const val TELEMETRY_PENDING_FILE = "voice_auth_pending.jsonl"
        const val STRUCTURED_TELEMETRY_TAG = "StructuredTelemetry"
        const val CONNECT_TIMEOUT_MS = 5000
        const val READ_TIMEOUT_MS = 8000
    }
}
