package com.vpsaker.fake_voice_detector.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult

@Composable
fun VoiceDetectorScreen(
    uiState: DetectorUiState,
    hasAudioPermission: Boolean,
    onRequestPermission: () -> Unit,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .background(
                brush = Brush.verticalGradient(
                    listOf(Color(0xFF032535), Color(0xFF075B6A), Color(0xFFCEE6E6))
                )
            )
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
            text = "Lớp bảo vệ bổ sung cho ASV: thu âm ngắn và đánh giá Bonafide/Spoof.",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.White.copy(alpha = 0.92f)
        )

        if (!hasAudioPermission) {
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
            return
        }

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
                    Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
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

        uiState.result?.let { result ->
            ResultCard(result = result)
        }

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
            Text(text = "Engine: ${result.modelName}")
        }
    }
}
