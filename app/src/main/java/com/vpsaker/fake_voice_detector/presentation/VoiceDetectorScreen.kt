package com.vpsaker.fake_voice_detector.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@Composable
fun VoiceDetectorScreen(
    uiState: DetectorUiState,
    hasAudioPermission: Boolean,
    onRequestPermission: () -> Unit,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onAsvScoreInputChange: (String) -> Unit,
    onSpoofThresholdChange: (Float) -> Unit,
    onAsvThresholdChange: (Float) -> Unit,
    onUseRemoteAsvChange: (Boolean) -> Unit,
    onAsvEndpointChange: (String) -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()
    Column(
        modifier = modifier
            .background(
                brush = Brush.verticalGradient(
                    listOf(Color(0xFF032535), Color(0xFF075B6A), Color(0xFFCEE6E6))
                )
            )
            .verticalScroll(scrollState)
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "Voice Spoofing Detector",
            style = MaterialTheme.typography.headlineSmall,
            color = Color.White,
            fontWeight = FontWeight.Bold
        )
        Text(
            text = "Lớp bảo vệ ASV: anti-spoof + fusion decision (ALLOW/REVIEW/BLOCK).",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.White.copy(alpha = 0.92f)
        )

        if (!hasAudioPermission) {
            PermissionCard(onRequestPermission = onRequestPermission)
            return
        }

        RecordingCard(
            uiState = uiState,
            onStartRecording = onStartRecording,
            onStopRecording = onStopRecording
        )

        FusionControlCard(
            asvScoreInput = uiState.asvScoreInput,
            spoofThreshold = uiState.spoofThreshold,
            asvThreshold = uiState.asvThreshold,
            useRemoteAsv = uiState.useRemoteAsv,
            asvEndpoint = uiState.asvEndpoint,
            lastAsvSource = uiState.lastAsvSource,
            lastAsvLatencyMs = uiState.lastAsvLatencyMs,
            onAsvScoreInputChange = onAsvScoreInputChange,
            onSpoofThresholdChange = onSpoofThresholdChange,
            onAsvThresholdChange = onAsvThresholdChange,
            onUseRemoteAsvChange = onUseRemoteAsvChange,
            onAsvEndpointChange = onAsvEndpointChange
        )

        uiState.result?.let { result ->
            ResultCard(result = result)
        }

        uiState.fusionDecisionResult?.let { fusion ->
            FusionDecisionCard(fusion)
        }

        SessionHistoryCard(sessions = uiState.sessions)

        uiState.errorMessage?.let { message ->
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFE1E1))) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(text = "Lỗi: $message", color = Color(0xFF7A0000))
                    OutlinedButton(onClick = onDismissError) {
                        Text("Đóng")
                    }
                }
            }
        }
    }
}

@Composable
private fun PermissionCard(onRequestPermission: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.94f))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Ứng dụng cần quyền microphone để phân tích giọng nói.")
            Button(onClick = onRequestPermission) {
                Text("Cấp quyền microphone")
            }
        }
    }
}

@Composable
private fun RecordingCard(
    uiState: DetectorUiState,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f))) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = if (uiState.isRecording) "Recording" else "Idle",
                    fontWeight = FontWeight.SemiBold
                )
                Text(text = "${uiState.recordingSeconds}s")
            }

            if (uiState.isAnalyzing) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator()
                    Text("Đang suy luận mô hình...")
                }
            }

            if (!uiState.isRecording) {
                Button(
                    onClick = onStartRecording,
                    enabled = !uiState.isAnalyzing,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Start Recording")
                }
            } else {
                OutlinedButton(
                    onClick = onStopRecording,
                    enabled = !uiState.isAnalyzing,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Stop & Analyze")
                }
            }
        }
    }
}

@Composable
private fun FusionControlCard(
    asvScoreInput: String,
    spoofThreshold: Float,
    asvThreshold: Float,
    useRemoteAsv: Boolean,
    asvEndpoint: String,
    lastAsvSource: String,
    lastAsvLatencyMs: Long,
    onAsvScoreInputChange: (String) -> Unit,
    onSpoofThresholdChange: (Float) -> Unit,
    onAsvThresholdChange: (Float) -> Unit,
    onUseRemoteAsvChange: (Boolean) -> Unit,
    onAsvEndpointChange: (String) -> Unit
) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f))) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("Fusion Controls", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            OutlinedTextField(
                value = asvScoreInput,
                onValueChange = onAsvScoreInputChange,
                label = { Text("ASV score (0.0 - 1.0)") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Use remote ASV backend")
                Switch(checked = useRemoteAsv, onCheckedChange = onUseRemoteAsvChange)
            }
            OutlinedTextField(
                value = asvEndpoint,
                onValueChange = onAsvEndpointChange,
                label = { Text("ASV endpoint URL") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )
            Text("ASV source: $lastAsvSource")
            Text("ASV latency: ${lastAsvLatencyMs}ms")

            Text("Spoof threshold: ${"%.2f".format(spoofThreshold)}")
            Slider(
                value = spoofThreshold,
                onValueChange = onSpoofThresholdChange,
                valueRange = 0.05f..0.95f
            )

            Text("ASV threshold: ${"%.2f".format(asvThreshold)}")
            Slider(
                value = asvThreshold,
                onValueChange = onAsvThresholdChange,
                valueRange = 0.05f..0.95f
            )
        }
    }
}

@Composable
private fun ResultCard(result: DetectionResult) {
    val spoofColor = if (result.isSpoof) Color(0xFFC0392B) else Color(0xFF1E8449)
    val spoofPercent = (result.spoofProbability * 100).toInt()

    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = if (result.isSpoof) "Kết quả: SPOOF" else "Kết quả: BONAFIDE",
                color = spoofColor,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(text = "Spoof probability: $spoofPercent%")
            LinearProgressIndicator(
                progress = { result.spoofProbability },
                modifier = Modifier.fillMaxWidth(),
                color = spoofColor
            )
            Text(text = "Confidence: ${(result.confidence * 100).toInt()}%")
            Text(text = "Duration: ${"%.2f".format(result.recordingDurationSec)}s")
            Text(text = "Decision threshold: ${"%.2f".format(result.threshold)}")
            Text(text = "Engine: ${result.modelName}")
        }
    }
}

@Composable
private fun FusionDecisionCard(result: FusionDecisionResult) {
    val color = when (result.decision) {
        AuthenticationDecision.ALLOW -> Color(0xFF1E8449)
        AuthenticationDecision.REVIEW -> Color(0xFFAF7F0C)
        AuthenticationDecision.BLOCK -> Color(0xFFC0392B)
    }

    Card(colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f))) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Fusion Decision: ${result.decision.name}",
                style = MaterialTheme.typography.titleMedium,
                color = color,
                fontWeight = FontWeight.Bold
            )
            Text("Reason: ${result.reason}")
            Text("ASV score: ${"%.2f".format(result.asvScore)}")
            Text("Spoof probability: ${"%.2f".format(result.spoofProbability)}")
            Text("Pass ASV threshold: ${if (result.meetsAsvThreshold) "YES" else "NO"}")
            Text("Pass spoof threshold: ${if (result.meetsSpoofThreshold) "YES" else "NO"}")
        }
    }
}

@Composable
private fun SessionHistoryCard(sessions: List<DetectionSession>) {
    Card(colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f))) {
        Column(
            modifier = Modifier
                .padding(16.dp)
                .heightIn(max = 280.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Recent Sessions", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            if (sessions.isEmpty()) {
                Text("Chưa có phiên nào.")
            } else {
                sessions.forEachIndexed { index, session ->
                    val time = formatTime(session.createdAtEpochMs)
                    Text(
                        text = "#${index + 1} $time | ${session.fusionDecision.decision.name} | spoof=${"%.2f".format(session.detectionResult.spoofProbability)} | asv=${"%.2f".format(session.fusionDecision.asvScore)}",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}

private fun formatTime(epochMs: Long): String {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    return formatter.format(Date(epochMs))
}
