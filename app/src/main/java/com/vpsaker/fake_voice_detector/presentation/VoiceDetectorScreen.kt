package com.vpsaker.fake_voice_detector.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
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
                    listOf(Color(0xFF021722), Color(0xFF094663), Color(0xFFE7F1F3))
                )
            )
            .verticalScroll(scrollState)
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        HeaderCard()

        SystemStatusCard(
            hasAudioPermission = hasAudioPermission,
            useRemoteAsv = uiState.useRemoteAsv,
            asvEndpoint = uiState.asvEndpoint,
            telemetryStatus = uiState.telemetryStatus,
            strictReleaseMode = uiState.strictReleaseMode
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

        uiState.fusionDecisionResult?.let { fusion ->
            FusionDecisionCard(fusion)
        }

        uiState.result?.let { result ->
            ResultCard(result = result)
        }

        FusionControlCard(
            strictReleaseMode = uiState.strictReleaseMode,
            asvScoreInput = uiState.asvScoreInput,
            spoofThreshold = uiState.spoofThreshold,
            asvThreshold = uiState.asvThreshold,
            useRemoteAsv = uiState.useRemoteAsv,
            asvEndpoint = uiState.asvEndpoint,
            lastAsvSource = uiState.lastAsvSource,
            lastAsvLatencyMs = uiState.lastAsvLatencyMs,
            telemetryStatus = uiState.telemetryStatus,
            lastTelemetryFlushCount = uiState.lastTelemetryFlushCount,
            onAsvScoreInputChange = onAsvScoreInputChange,
            onSpoofThresholdChange = onSpoofThresholdChange,
            onAsvThresholdChange = onAsvThresholdChange,
            onUseRemoteAsvChange = onUseRemoteAsvChange,
            onAsvEndpointChange = onAsvEndpointChange
        )

        SessionHistoryCard(sessions = uiState.sessions)

        uiState.errorMessage?.let { message ->
            Card(
                colors = CardDefaults.cardColors(containerColor = Color(0xFFFFE4E4)),
                shape = RoundedCornerShape(16.dp)
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(text = "Lỗi: $message", color = Color(0xFF7A0000), fontWeight = FontWeight.SemiBold)
                    OutlinedButton(onClick = onDismissError) {
                        Text("Đóng")
                    }
                }
            }
        }
    }
}

@Composable
private fun HeaderCard() {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFFEAF6F8).copy(alpha = 0.95f)),
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(
                text = "Voice Spoofing Detector",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.ExtraBold,
                color = Color(0xFF062D3B)
            )
            Text(
                text = "Làm theo 3 bước: (1) Kiểm tra trạng thái, (2) Ghi âm, (3) Xem quyết định ALLOW/REVIEW/BLOCK.",
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFF1E495A)
            )
        }
    }
}

@Composable
private fun SystemStatusCard(
    hasAudioPermission: Boolean,
    useRemoteAsv: Boolean,
    asvEndpoint: String,
    telemetryStatus: String,
    strictReleaseMode: Boolean
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.95f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            Text("Bước 1: Trạng thái hệ thống", fontWeight = FontWeight.Bold)
            StatusLine("Microphone", if (hasAudioPermission) "Đã cấp quyền" else "Chưa cấp quyền")
            StatusLine("ASV backend", if (useRemoteAsv) "Đang bật" else "Đang tắt")
            StatusLine("Endpoint", if (asvEndpoint.isBlank()) "Chưa cấu hình" else asvEndpoint)
            StatusLine("Telemetry", telemetryStatus)
            if (strictReleaseMode) {
                Text("Release mode: fallback đã bị khóa để đảm bảo an toàn.", color = Color(0xFF7D4E00))
            }
        }
    }
}

@Composable
private fun PermissionCard(onRequestPermission: () -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.95f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("Bước 2: Cấp quyền micro", fontWeight = FontWeight.Bold)
            Text("Ứng dụng cần quyền ghi âm để phân tích giọng nói.")
            Button(onClick = onRequestPermission, modifier = Modifier.fillMaxWidth()) {
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
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("Bước 2: Ghi âm và phân tích", fontWeight = FontWeight.Bold)
            Text(
                text = if (uiState.isRecording) "Đang ghi âm... hãy đọc câu xác thực" else "Sẵn sàng ghi âm",
                color = if (uiState.isRecording) Color(0xFF0D6A43) else Color(0xFF3F4E55)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = if (uiState.isRecording) "Recording" else "Idle", fontWeight = FontWeight.SemiBold)
                Text(text = "${uiState.recordingSeconds}s")
            }

            if (uiState.isAnalyzing) {
                Row(
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    CircularProgressIndicator()
                    Text("Đang suy luận anti-spoof + gọi ASV backend...")
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
    strictReleaseMode: Boolean,
    asvScoreInput: String,
    spoofThreshold: Float,
    asvThreshold: Float,
    useRemoteAsv: Boolean,
    asvEndpoint: String,
    lastAsvSource: String,
    lastAsvLatencyMs: Long,
    telemetryStatus: String,
    lastTelemetryFlushCount: Int,
    onAsvScoreInputChange: (String) -> Unit,
    onSpoofThresholdChange: (Float) -> Unit,
    onAsvThresholdChange: (Float) -> Unit,
    onUseRemoteAsvChange: (Boolean) -> Unit,
    onAsvEndpointChange: (String) -> Unit
) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text("Bước 3: Cấu hình nâng cao", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)

            if (!strictReleaseMode) {
                OutlinedTextField(
                    value = asvScoreInput,
                    onValueChange = onAsvScoreInputChange,
                    label = { Text("Manual ASV score (debug)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            } else {
                Text("Release mode: manual ASV đã tắt.")
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Use remote ASV backend")
                Switch(
                    checked = if (strictReleaseMode) true else useRemoteAsv,
                    onCheckedChange = onUseRemoteAsvChange,
                    enabled = !strictReleaseMode
                )
            }

            OutlinedTextField(
                value = asvEndpoint,
                onValueChange = onAsvEndpointChange,
                label = { Text("ASV endpoint URL") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            Text("Spoof threshold: ${"%.2f".format(spoofThreshold)}")
            Slider(value = spoofThreshold, onValueChange = onSpoofThresholdChange, valueRange = 0.05f..0.95f)

            Text("ASV threshold: ${"%.2f".format(asvThreshold)}")
            Slider(value = asvThreshold, onValueChange = onAsvThresholdChange, valueRange = 0.05f..0.95f)

            Text("ASV source: $lastAsvSource | latency: ${lastAsvLatencyMs}ms")
            Text("Telemetry: $telemetryStatus | flushed: $lastTelemetryFlushCount")
        }
    }
}

@Composable
private fun ResultCard(result: DetectionResult) {
    val spoofColor = if (result.isSpoof) Color(0xFFBC2D1F) else Color(0xFF1E8449)
    val spoofPercent = (result.spoofProbability * 100).toInt()

    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Bước 3: Kết quả anti-spoof", fontWeight = FontWeight.Bold)
            Text(
                text = if (result.isSpoof) "Kết quả: SPOOF" else "Kết quả: BONAFIDE",
                color = spoofColor,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.ExtraBold
            )
            Text(text = "Spoof probability: $spoofPercent%")
            LinearProgressIndicator(
                progress = { result.spoofProbability },
                modifier = Modifier.fillMaxWidth(),
                color = spoofColor
            )
            Text(text = "Confidence: ${(result.confidence * 100).toInt()}%")
            Text(text = "Duration: ${"%.2f".format(result.recordingDurationSec)}s")
            Text(text = "Threshold: ${"%.2f".format(result.threshold)} | Engine: ${result.modelName}")
        }
    }
}

@Composable
private fun FusionDecisionCard(result: FusionDecisionResult) {
    val color = when (result.decision) {
        AuthenticationDecision.ALLOW -> Color(0xFF1E8449)
        AuthenticationDecision.REVIEW -> Color(0xFFA87503)
        AuthenticationDecision.BLOCK -> Color(0xFFC0392B)
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Quyết định cuối", fontWeight = FontWeight.Bold)
            Text(
                text = result.decision.name,
                style = MaterialTheme.typography.headlineSmall,
                color = color,
                fontWeight = FontWeight.ExtraBold
            )
            Text("Reason: ${result.reason}")
            Text("ASV score: ${"%.2f".format(result.asvScore)} | Spoof: ${"%.2f".format(result.spoofProbability)}")
            Text("Pass ASV: ${if (result.meetsAsvThreshold) "YES" else "NO"} | Pass spoof: ${if (result.meetsSpoofThreshold) "YES" else "NO"}")
        }
    }
}

@Composable
private fun SessionHistoryCard(sessions: List<DetectionSession>) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.96f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(
            modifier = Modifier
                .padding(16.dp)
                .heightIn(max = 280.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text("Lịch sử gần đây", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
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

@Composable
private fun StatusLine(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = Color(0xFF334750))
        Text(value, color = Color(0xFF0D536A), fontWeight = FontWeight.SemiBold)
    }
}

private fun formatTime(epochMs: Long): String {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    return formatter.format(Date(epochMs))
}
