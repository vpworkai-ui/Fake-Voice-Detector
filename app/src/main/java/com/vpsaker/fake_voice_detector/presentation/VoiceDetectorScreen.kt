package com.vpsaker.fake_voice_detector.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
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
    onStopAndSaveSample: () -> Unit,
    onAsvScoreInputChange: (String) -> Unit,
    onSpoofThresholdChange: (Float) -> Unit,
    onAsvThresholdChange: (Float) -> Unit,
    onUseRemoteAsvChange: (Boolean) -> Unit,
    onAsvEndpointChange: (String) -> Unit,
    onDatasetLabelChange: (String) -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scrollState = rememberScrollState()

    Column(
        modifier = modifier
            .background(
                Brush.verticalGradient(
                    listOf(Color(0xFF091423), Color(0xFF133A55), Color(0xFFE6EFF1))
                )
            )
            .verticalScroll(scrollState)
            .padding(horizontal = 14.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        HeroCard()

        SectionCard(title = "01. Tổng quan") {
            StatusPillRow(
                leftLabel = "Microphone",
                leftValue = if (hasAudioPermission) "Ready" else "Missing",
                rightLabel = "ASV",
                rightValue = if (uiState.useRemoteAsv) "Remote" else "Manual"
            )
            StatusPillRow(
                leftLabel = "Telemetry",
                leftValue = uiState.telemetryStatus,
                rightLabel = "Mode",
                rightValue = if (uiState.strictReleaseMode) "Release" else "Debug"
            )
            Text(
                text = "Endpoint: ${if (uiState.asvEndpoint.isBlank()) "(chưa cấu hình)" else uiState.asvEndpoint}",
                style = MaterialTheme.typography.bodySmall,
                color = Color(0xFF2D3F48)
            )
        }

        if (!hasAudioPermission) {
            SectionCard(title = "02. Cấp quyền bắt buộc") {
                Text("App cần quyền microphone để xử lý anti-spoof.")
                Button(onClick = onRequestPermission, modifier = Modifier.fillMaxWidth()) {
                    Text("Cấp quyền microphone")
                }
            }
            return
        }

        SectionCard(title = "02. Ghi âm & phân tích") {
            Text(
                text = if (uiState.isRecording) "Đang ghi âm... đọc câu xác thực rõ ràng." else "Nhấn Start Recording để bắt đầu.",
                color = if (uiState.isRecording) Color(0xFF0D6A43) else Color(0xFF364B56)
            )
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Badge(text = if (uiState.isRecording) "RECORDING" else "IDLE", accent = Color(0xFF0B5C7C))
                Text("${uiState.recordingSeconds}s", fontWeight = FontWeight.Bold)
            }

            if (uiState.isAnalyzing) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    Text("Đang suy luận anti-spoof + fusion...")
                }
            }

            if (!uiState.isRecording) {
                Button(onClick = onStartRecording, enabled = !uiState.isAnalyzing, modifier = Modifier.fillMaxWidth()) {
                    Text("Start Recording")
                }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    OutlinedButton(
                        onClick = onStopRecording,
                        enabled = !uiState.isAnalyzing,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Stop & Analyze")
                    }
                    Button(
                        onClick = onStopAndSaveSample,
                        enabled = !uiState.isAnalyzing,
                        modifier = Modifier.weight(1f)
                    ) {
                        Text("Stop & Save")
                    }
                }
            }
        }

        uiState.fusionDecisionResult?.let { decision ->
            SectionCard(title = "03. Quyết định cuối") {
                DecisionBlock(decision)
            }
        }

        uiState.result?.let { result ->
            SectionCard(title = "04. Chi tiết anti-spoof") {
                ResultBlock(result)
            }
        }

        SectionCard(title = "05. Cấu hình nâng cao") {
            if (!uiState.strictReleaseMode) {
                OutlinedTextField(
                    value = uiState.asvScoreInput,
                    onValueChange = onAsvScoreInputChange,
                    label = { Text("Manual ASV score (debug)") },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true
                )
            } else {
                Text("Release mode: manual ASV bị tắt.")
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text("Use remote ASV backend")
                Switch(
                    checked = if (uiState.strictReleaseMode) true else uiState.useRemoteAsv,
                    onCheckedChange = onUseRemoteAsvChange,
                    enabled = !uiState.strictReleaseMode
                )
            }

            OutlinedTextField(
                value = uiState.asvEndpoint,
                onValueChange = onAsvEndpointChange,
                label = { Text("ASV endpoint URL") },
                modifier = Modifier.fillMaxWidth(),
                singleLine = true
            )

            HorizontalDivider()

            Text("Spoof threshold: ${"%.2f".format(uiState.spoofThreshold)}")
            Slider(value = uiState.spoofThreshold, onValueChange = onSpoofThresholdChange, valueRange = 0.05f..0.95f)

            Text("ASV threshold: ${"%.2f".format(uiState.asvThreshold)}")
            Slider(value = uiState.asvThreshold, onValueChange = onAsvThresholdChange, valueRange = 0.05f..0.95f)

            Text("ASV source: ${uiState.lastAsvSource} | latency: ${uiState.lastAsvLatencyMs}ms")
            Text("Telemetry flushed: ${uiState.lastTelemetryFlushCount}")
        }

        SectionCard(title = "06. Thu dataset") {
            Text("Chọn nhãn trước khi ghi âm, sau đó bấm Start Recording rồi Stop & Save.")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedButton(
                    onClick = { onDatasetLabelChange("bonafide") },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(if (uiState.datasetLabel == "bonafide") "BONAFIDE ✓" else "BONAFIDE")
                }
                OutlinedButton(
                    onClick = { onDatasetLabelChange("spoof") },
                    modifier = Modifier.weight(1f)
                ) {
                    Text(if (uiState.datasetLabel == "spoof") "SPOOF ✓" else "SPOOF")
                }
            }
            Text("Current label: ${uiState.datasetLabel}")
            Text("Saved bonafide: ${uiState.savedBonafideCount} | saved spoof: ${uiState.savedSpoofCount}")
            if (uiState.isSavingSample) {
                Text("Đang lưu file mẫu...")
            }
            uiState.lastSavedSamplePath?.let { path ->
                Text("Last saved: $path", style = MaterialTheme.typography.bodySmall)
            }
        }

        SectionCard(title = "07. Lịch sử phiên") {
            if (uiState.sessions.isEmpty()) {
                Text("Chưa có phiên nào.")
            } else {
                SessionHistoryBlock(uiState.sessions)
            }
        }

        uiState.errorMessage?.let { message ->
            Card(colors = CardDefaults.cardColors(containerColor = Color(0xFFFFE5E5))) {
                Column(modifier = Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Lỗi: $message", color = Color(0xFF7A0000), fontWeight = FontWeight.SemiBold)
                    OutlinedButton(onClick = onDismissError) { Text("Đóng") }
                }
            }
        }
    }
}

@Composable
private fun HeroCard() {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color(0xFFECF5F8).copy(alpha = 0.97f)),
        shape = RoundedCornerShape(18.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Voice Spoofing Detector", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold, color = Color(0xFF082A38))
            Text("Mục tiêu: xác định BONAFIDE/SPOOF và đưa quyết định ALLOW/REVIEW/BLOCK.", color = Color(0xFF25515F))
            Text("Flow chuẩn: 01 Tổng quan -> 02 Ghi âm -> 03 Quyết định -> 05 Cấu hình.", style = MaterialTheme.typography.bodySmall, color = Color(0xFF355A67))
        }
    }
}

@Composable
private fun SectionCard(title: String, content: @Composable ColumnScope.() -> Unit) {
    Card(
        colors = CardDefaults.cardColors(containerColor = Color.White.copy(alpha = 0.97f)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, color = Color(0xFF19495E), fontWeight = FontWeight.Bold)
            content()
        }
    }
}

@Composable
private fun StatusPillRow(
    leftLabel: String,
    leftValue: String,
    rightLabel: String,
    rightValue: String
) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Surface(shape = RoundedCornerShape(20.dp), color = Color(0xFFE3F2F7), modifier = Modifier.weight(1f)) {
            Column(modifier = Modifier.padding(10.dp)) {
                Text(leftLabel, style = MaterialTheme.typography.bodySmall, color = Color(0xFF516973))
                Text(leftValue, fontWeight = FontWeight.Bold, color = Color(0xFF0C566F))
            }
        }
        Surface(shape = RoundedCornerShape(20.dp), color = Color(0xFFE8F7E9), modifier = Modifier.weight(1f)) {
            Column(modifier = Modifier.padding(10.dp)) {
                Text(rightLabel, style = MaterialTheme.typography.bodySmall, color = Color(0xFF516973))
                Text(rightValue, fontWeight = FontWeight.Bold, color = Color(0xFF1A6D46))
            }
        }
    }
}

@Composable
private fun Badge(text: String, accent: Color) {
    Surface(shape = RoundedCornerShape(50), color = accent.copy(alpha = 0.15f)) {
        Text(text = text, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp), color = accent, fontWeight = FontWeight.Bold)
    }
}

@Composable
private fun DecisionBlock(result: FusionDecisionResult) {
    val color = when (result.decision) {
        AuthenticationDecision.ALLOW -> Color(0xFF1E8449)
        AuthenticationDecision.REVIEW -> Color(0xFFA97504)
        AuthenticationDecision.BLOCK -> Color(0xFFC0392B)
    }

    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Box(modifier = Modifier.size(14.dp).background(color, CircleShape))
        Text(result.decision.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.ExtraBold, color = color)
    }
    Text("Reason: ${result.reason}")
    Text("ASV: ${"%.2f".format(result.asvScore)} | Spoof: ${"%.2f".format(result.spoofProbability)}")
    Text("Pass ASV: ${if (result.meetsAsvThreshold) "YES" else "NO"} | Pass spoof: ${if (result.meetsSpoofThreshold) "YES" else "NO"}")
}

@Composable
private fun ResultBlock(result: DetectionResult) {
    val color = if (result.isSpoof) Color(0xFFC0392B) else Color(0xFF1E8449)
    Text(
        text = if (result.isSpoof) "Kết quả anti-spoof: SPOOF" else "Kết quả anti-spoof: BONAFIDE",
        color = color,
        fontWeight = FontWeight.ExtraBold
    )
    LinearProgressIndicator(progress = { result.spoofProbability }, modifier = Modifier.fillMaxWidth(), color = color)
    Text("Spoof probability: ${(result.spoofProbability * 100).toInt()}%")
    Text("Confidence: ${(result.confidence * 100).toInt()}%")
    Text("Duration: ${"%.2f".format(result.recordingDurationSec)}s")
    Text("Threshold: ${"%.2f".format(result.threshold)} | Engine: ${result.modelName}")
}

@Composable
private fun SessionHistoryBlock(sessions: List<DetectionSession>) {
    Column(modifier = Modifier.heightIn(max = 260.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
        sessions.forEachIndexed { index, session ->
            Text(
                "#${index + 1} ${formatTime(session.createdAtEpochMs)} | ${session.fusionDecision.decision.name} | spoof=${"%.2f".format(session.detectionResult.spoofProbability)} | asv=${"%.2f".format(session.fusionDecision.asvScore)}",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

private fun formatTime(epochMs: Long): String {
    val formatter = SimpleDateFormat("HH:mm:ss", Locale.getDefault())
    return formatter.format(Date(epochMs))
}
