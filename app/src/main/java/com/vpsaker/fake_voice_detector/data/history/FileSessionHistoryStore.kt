package com.vpsaker.fake_voice_detector.data.history

import android.content.Context
import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult
import org.json.JSONArray
import org.json.JSONObject
import java.io.File

class FileSessionHistoryStore(
    private val context: Context
) {

    fun loadSessions(): List<DetectionSession> {
        val file = historyFile()
        if (!file.exists()) return emptyList()

        return runCatching {
            val raw = file.readText(Charsets.UTF_8)
            if (raw.isBlank()) return@runCatching emptyList()

            val array = JSONArray(raw)
            buildList {
                for (index in 0 until array.length()) {
                    add(parseSession(array.getJSONObject(index)))
                }
            }
        }.getOrDefault(emptyList())
    }

    fun saveSessions(sessions: List<DetectionSession>) {
        val array = JSONArray()
        sessions.forEach { session -> array.put(serializeSession(session)) }
        historyFile().writeText(array.toString(), Charsets.UTF_8)
    }

    private fun serializeSession(session: DetectionSession): JSONObject {
        return JSONObject().apply {
            put("createdAtEpochMs", session.createdAtEpochMs)
            put("detectionResult", JSONObject().apply {
                put("spoofProbability", session.detectionResult.spoofProbability)
                put("threshold", session.detectionResult.threshold)
                put("modelName", session.detectionResult.modelName)
                put("recordingDurationSec", session.detectionResult.recordingDurationSec)
                put("featureExtractionMs", session.detectionResult.featureExtractionMs)
                put("inferenceMs", session.detectionResult.inferenceMs)
                put("inputMetadata", JSONObject().apply {
                    put("inputSource", session.detectionResult.inputMetadata.inputSource)
                    put("fileName", session.detectionResult.inputMetadata.fileName)
                    put("fileHash", session.detectionResult.inputMetadata.fileHash)
                    put("originalSampleRateHz", session.detectionResult.inputMetadata.originalSampleRateHz)
                    put("normalizedSampleRateHz", session.detectionResult.inputMetadata.normalizedSampleRateHz)
                    put("channelCount", session.detectionResult.inputMetadata.channelCount)
                })
                put("acousticFeatures", JSONObject().apply {
                    put("rms", session.detectionResult.acousticFeatures.rms)
                    put("meanAbs", session.detectionResult.acousticFeatures.meanAbs)
                    put("zcr", session.detectionResult.acousticFeatures.zcr)
                    put("peak", session.detectionResult.acousticFeatures.peak)
                    put("crestFactor", session.detectionResult.acousticFeatures.crestFactor)
                    put("clippingRatio", session.detectionResult.acousticFeatures.clippingRatio)
                    put("dynamicRange", session.detectionResult.acousticFeatures.dynamicRange)
                    put("durationSec", session.detectionResult.acousticFeatures.durationSec)
                })
            })
            put("fusionDecision", JSONObject().apply {
                put("decision", session.fusionDecision.decision.name)
                put("reason", session.fusionDecision.reason)
                put("spoofProbability", session.fusionDecision.spoofProbability)
                put("spoofThreshold", session.fusionDecision.spoofThreshold)
                put("confidence", session.fusionDecision.confidence)
                put("meetsSpoofThreshold", session.fusionDecision.meetsSpoofThreshold)
            })
        }
    }

    private fun parseSession(json: JSONObject): DetectionSession {
        val detection = json.getJSONObject("detectionResult")
        val fusion = json.getJSONObject("fusionDecision")
        val inputMetadata = detection.optJSONObject("inputMetadata")
        val acousticFeatures = detection.optJSONObject("acousticFeatures")

        return DetectionSession(
            createdAtEpochMs = json.getLong("createdAtEpochMs"),
            detectionResult = DetectionResult(
                spoofProbability = detection.getDouble("spoofProbability").toFloat(),
                threshold = detection.optDouble("threshold", 0.25).toFloat(),
                modelName = detection.optString("modelName", "unknown"),
                recordingDurationSec = detection.optDouble("recordingDurationSec", 0.0).toFloat(),
                featureExtractionMs = detection.optLong("featureExtractionMs", 0L),
                inferenceMs = detection.optLong("inferenceMs", 0L),
                inputMetadata = com.vpsaker.fake_voice_detector.domain.model.AudioInputMetadata(
                    inputSource = inputMetadata?.optString("inputSource", "unknown") ?: "unknown",
                    fileName = inputMetadata?.optString("fileName")?.takeIf { it.isNotBlank() },
                    fileHash = inputMetadata?.optString("fileHash")?.takeIf { it.isNotBlank() },
                    originalSampleRateHz = inputMetadata?.optInt("originalSampleRateHz", 0) ?: 0,
                    normalizedSampleRateHz = inputMetadata?.optInt("normalizedSampleRateHz", 0) ?: 0,
                    channelCount = inputMetadata?.optInt("channelCount", 0) ?: 0,
                ),
                acousticFeatures = com.vpsaker.fake_voice_detector.domain.model.AcousticFeatureSnapshot(
                    rms = acousticFeatures?.optDouble("rms", 0.0)?.toFloat() ?: 0f,
                    meanAbs = acousticFeatures?.optDouble("meanAbs", 0.0)?.toFloat() ?: 0f,
                    zcr = acousticFeatures?.optDouble("zcr", 0.0)?.toFloat() ?: 0f,
                    peak = acousticFeatures?.optDouble("peak", 0.0)?.toFloat() ?: 0f,
                    crestFactor = acousticFeatures?.optDouble("crestFactor", 0.0)?.toFloat() ?: 0f,
                    clippingRatio = acousticFeatures?.optDouble("clippingRatio", 0.0)?.toFloat() ?: 0f,
                    dynamicRange = acousticFeatures?.optDouble("dynamicRange", 0.0)?.toFloat() ?: 0f,
                    durationSec = acousticFeatures?.optDouble("durationSec", 0.0)?.toFloat() ?: 0f,
                )
            ),
            fusionDecision = FusionDecisionResult(
                decision = AuthenticationDecision.valueOf(fusion.getString("decision")),
                reason = fusion.optString("reason", ""),
                spoofProbability = fusion.optDouble("spoofProbability", 0.0).toFloat(),
                spoofThreshold = fusion.optDouble("spoofThreshold", 0.25).toFloat(),
                confidence = fusion.optDouble("confidence", 0.0).toFloat(),
                meetsSpoofThreshold = fusion.optBoolean("meetsSpoofThreshold", false)
            )
        )
    }

    private fun historyFile(): File {
        val directory = File(context.filesDir, HISTORY_DIR).apply { mkdirs() }
        return File(directory, HISTORY_FILE)
    }

    private companion object {
        const val HISTORY_DIR = "history"
        const val HISTORY_FILE = "detection_sessions.json"
    }
}
