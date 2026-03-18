package com.vpsaker.fake_voice_detector.data.telemetry

import android.content.Context
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.repository.TelemetryRepository
import org.json.JSONObject
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

class FileTelemetryRepository(
    private val context: Context
) : TelemetryRepository {

    override suspend fun logAuthenticationEvent(event: AuthTelemetryEvent): Result<Unit> {
        return runCatching {
            val directory = telemetryDirectory()
            File(directory, TELEMETRY_LOG_FILE).appendText(serialize(event) + "\n")
            File(directory, TELEMETRY_PENDING_FILE).appendText(serialize(event) + "\n")
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
            put("spoofProbability", event.spoofProbability)
            put("asvScore", event.asvScore)
            put("decision", event.decision)
            put("reason", event.reason)
            put("asvSource", event.asvSource)
            put("asvLatencyMs", event.asvLatencyMs)
            put("modelName", event.modelName)
            put("recordingDurationSec", event.recordingDurationSec)
        }.toString()
    }

    private fun telemetryDirectory(): File {
        return File(context.filesDir, TELEMETRY_DIR).apply { mkdirs() }
    }

    private companion object {
        const val TELEMETRY_DIR = "telemetry"
        const val TELEMETRY_LOG_FILE = "voice_auth_events.jsonl"
        const val TELEMETRY_PENDING_FILE = "voice_auth_pending.jsonl"
        const val CONNECT_TIMEOUT_MS = 5000
        const val READ_TIMEOUT_MS = 8000
    }
}
