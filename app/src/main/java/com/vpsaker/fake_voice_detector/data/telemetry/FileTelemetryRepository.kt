package com.vpsaker.fake_voice_detector.data.telemetry

import android.content.Context
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.repository.TelemetryRepository
import org.json.JSONObject
import java.io.File

class FileTelemetryRepository(
    private val context: Context
) : TelemetryRepository {

    override suspend fun logAuthenticationEvent(event: AuthTelemetryEvent): Result<Unit> {
        return runCatching {
            val directory = File(context.filesDir, TELEMETRY_DIR).apply { mkdirs() }
            val logFile = File(directory, TELEMETRY_FILE)
            logFile.appendText(serialize(event) + "\n")
        }
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

    private companion object {
        const val TELEMETRY_DIR = "telemetry"
        const val TELEMETRY_FILE = "voice_auth_events.jsonl"
    }
}
