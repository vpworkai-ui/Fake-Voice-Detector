package com.vpsaker.fake_voice_detector.data.asv

import com.vpsaker.fake_voice_detector.domain.model.AsvScoreRequest
import com.vpsaker.fake_voice_detector.domain.model.AsvScoreResult
import com.vpsaker.fake_voice_detector.domain.repository.AsvScoreRepository
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

class HttpAsvScoreRepository(
    private val apiKey: String = ""
) : AsvScoreRepository {

    override suspend fun fetchAsvScore(request: AsvScoreRequest): Result<AsvScoreResult> {
        return runCatching {
            val startedAt = System.currentTimeMillis()
            val endpointUrl = URL(request.endpoint)
            val connection = (endpointUrl.openConnection() as HttpURLConnection).apply {
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
                writer.write(buildPayload(request).toString())
                writer.flush()
            }

            val responseCode = connection.responseCode
            if (responseCode !in 200..299) {
                val errorText = connection.errorStream?.bufferedReader()?.use { it.readText() }.orEmpty()
                throw IllegalStateException("ASV backend error $responseCode: $errorText")
            }

            val responseText = connection.inputStream.bufferedReader().use { it.readText() }
            val json = JSONObject(responseText)
            val score = json.optDouble("asvScore", Double.NaN)
            if (score.isNaN()) {
                throw IllegalStateException("Backend response missing asvScore")
            }

            val elapsed = (System.currentTimeMillis() - startedAt).coerceAtLeast(0)
            AsvScoreResult(
                score = score.toFloat().coerceIn(0f, 1f),
                source = json.optString("source", "remote"),
                latencyMs = elapsed
            )
        }
    }

    private fun buildPayload(request: AsvScoreRequest): JSONObject {
        return JSONObject().apply {
            put("spoofProbability", request.spoofProbability)
            put("recordingDurationSec", request.recordingDurationSec)
            put("sessionTimestampMs", request.sessionTimestampMs)
        }
    }

    private companion object {
        const val CONNECT_TIMEOUT_MS = 5000
        const val READ_TIMEOUT_MS = 8000
    }
}
