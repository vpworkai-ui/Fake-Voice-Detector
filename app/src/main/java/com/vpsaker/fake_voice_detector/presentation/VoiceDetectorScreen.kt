package com.vpsaker.fake_voice_detector.presentation

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.EaseInOut
import androidx.compose.animation.core.EaseOut
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.animation.expandVertically
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.shrinkVertically
import androidx.compose.animation.slideInVertically
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material.icons.filled.Link
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Speed
import androidx.compose.material.icons.filled.Storage
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.scale
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.DetectionResult
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

// ─── Palette ──────────────────────────────────────────────────────────────────
private val Navy900   = Color(0xFF060F1F)
private val Navy800   = Color(0xFF0A1628)
private val Navy700   = Color(0xFF0F2744)
private val Navy600   = Color(0xFF163558)
private val Teal500   = Color(0xFF0B8FAC)
private val Teal400   = Color(0xFF17B0D0)
private val TealBg    = Color(0xFFE0F7FB)
private val Green500  = Color(0xFF1DB954)
private val GreenBg   = Color(0xFFE6F9EE)
private val Red500    = Color(0xFFE53935)
private val RedBg     = Color(0xFFFFEBEE)
private val Orange500 = Color(0xFFF57C00)
private val OrangeBg  = Color(0xFFFFF3E0)
private val Purple    = Color(0xFF7B61FF)
private val PurpleBg  = Color(0xFFF0ECFF)
private val Surface0  = Color(0xFFF4F8FA)
private val Surface1  = Color(0xFFFFFFFF)
private val OnSurface = Color(0xFF0D2137)
private val OnSurfaceMid = Color(0xFF4A6572)
private val OnSurfaceLow = Color(0xFF8FA8B4)

private val detectGradient = Brush.verticalGradient(
    listOf(Navy900, Navy800, Navy700, Navy600, Color(0xFF1A4570))
)

// ─── Main Screen ──────────────────────────────────────────────────────────────
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
    onExportCsv: () -> Unit,
    modifier: Modifier = Modifier
) {
    var selectedTab by rememberSaveable { mutableIntStateOf(0) }

    Scaffold(
        modifier       = modifier,
        containerColor = Surface0,
        bottomBar = {
            NavigationBar(
                containerColor = Navy800,
                tonalElevation = 0.dp
            ) {
                listOf(
                    Triple(0, "Phát hiện", Icons.Filled.Mic),
                    Triple(1, "Lịch sử",   Icons.Filled.History),
                    Triple(2, "Cài đặt",   Icons.Filled.Settings)
                ).forEach { (idx, label, icon) ->
                    NavigationBarItem(
                        selected = selectedTab == idx,
                        onClick  = { selectedTab = idx },
                        icon = {
                            Icon(icon, contentDescription = label, modifier = Modifier.size(22.dp))
                        },
                        label = {
                            Text(label, fontSize = 11.sp, fontWeight = FontWeight.Medium)
                        },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor   = Teal400,
                            selectedTextColor   = Teal400,
                            unselectedIconColor = OnSurfaceLow,
                            unselectedTextColor = OnSurfaceLow,
                            indicatorColor      = Teal500.copy(alpha = 0.15f)
                        )
                    )
                }
            }
        }
    ) { pad ->
        when (selectedTab) {
            0 -> DetectTab(
                uiState = uiState,
                hasAudioPermission  = hasAudioPermission,
                onRequestPermission = onRequestPermission,
                onStartRecording    = onStartRecording,
                onStopRecording     = onStopRecording,
                onStopAndSaveSample = onStopAndSaveSample,
                onDismissError      = onDismissError,
                modifier            = Modifier.padding(pad)
            )
            1 -> HistoryTab(
                sessions      = uiState.sessions,
                isExporting   = uiState.isExporting,
                lastExportPath = uiState.lastExportPath,
                onExportCsv   = onExportCsv,
                modifier      = Modifier.padding(pad)
            )
            2 -> SettingsTab(
                uiState                = uiState,
                onAsvScoreInputChange  = onAsvScoreInputChange,
                onSpoofThresholdChange = onSpoofThresholdChange,
                onAsvThresholdChange   = onAsvThresholdChange,
                onUseRemoteAsvChange   = onUseRemoteAsvChange,
                onAsvEndpointChange    = onAsvEndpointChange,
                onDatasetLabelChange   = onDatasetLabelChange,
                modifier               = Modifier.padding(pad)
            )
        }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
//  TAB 1 — PHÁT HIỆN
// ══════════════════════════════════════════════════════════════════════════════
@Composable
private fun DetectTab(
    uiState: DetectorUiState,
    hasAudioPermission: Boolean,
    onRequestPermission: () -> Unit,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onStopAndSaveSample: () -> Unit,
    onDismissError: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
    ) {
        // ── Dark hero zone ────────────────────────────────────────────────────
        Box(
            modifier         = Modifier
                .fillMaxWidth()
                .background(detectGradient)
                .padding(top = 28.dp, bottom = 36.dp),
            contentAlignment = Alignment.Center
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(20.dp)
            ) {
                // App label
                Row(
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(Icons.Filled.Shield, contentDescription = null, tint = Teal400, modifier = Modifier.size(18.dp))
                    Text(
                        "DEEPFAKE VOICE DETECTOR",
                        fontSize   = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color      = Teal400,
                        letterSpacing = 1.5.sp
                    )
                }

                if (!hasAudioPermission) {
                    PermissionHeroCard(onRequestPermission)
                } else {
                    RecordingHero(
                        uiState             = uiState,
                        onStartRecording    = onStartRecording,
                        onStopRecording     = onStopRecording,
                        onStopAndSaveSample = onStopAndSaveSample
                    )
                }
            }
        }

        // ── Results zone (light) ───────────────────────────────────────────
        Column(
            modifier            = Modifier
                .fillMaxWidth()
                .background(Surface0)
                .padding(horizontal = 16.dp, vertical = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            uiState.errorMessage?.let { ErrorBanner(message = it, onDismiss = onDismissError) }

            AnimatedVisibility(
                visible = uiState.fusionDecisionResult != null,
                enter   = fadeIn() + slideInVertically { it / 2 },
                exit    = fadeOut()
            ) {
                uiState.fusionDecisionResult?.let { DecisionResultCard(it) }
            }

            AnimatedVisibility(
                visible = uiState.result != null,
                enter   = fadeIn(tween(300, delayMillis = 100)) + slideInVertically(tween(300, delayMillis = 100)) { it / 2 },
                exit    = fadeOut()
            ) {
                uiState.result?.let { SpoofDetailCard(it) }
            }

            AnimatedVisibility(
                visible = uiState.result != null,
                enter   = fadeIn(tween(300, delayMillis = 200)) + slideInVertically(tween(300, delayMillis = 200)) { it / 2 },
                exit    = fadeOut()
            ) {
                uiState.result?.let { FeaturesCard(it) }
            }

            AnimatedVisibility(
                visible = uiState.lastTotalPipelineMs > 0,
                enter   = fadeIn(tween(300, delayMillis = 300)) + slideInVertically(tween(300, delayMillis = 300)) { it / 2 },
                exit    = fadeOut()
            ) {
                PerformanceCard(uiState)
            }

            if (uiState.fusionDecisionResult == null && uiState.result == null && !uiState.isRecording && !uiState.isAnalyzing) {
                DetectEmptyHint()
            }
        }
    }
}

@Composable
private fun RecordingHero(
    uiState: DetectorUiState,
    onStartRecording: () -> Unit,
    onStopRecording: () -> Unit,
    onStopAndSaveSample: () -> Unit
) {
    val isRecording  = uiState.isRecording
    val isAnalyzing  = uiState.isAnalyzing

    // Pulse animation when recording
    val infiniteTransition = rememberInfiniteTransition(label = "rec_pulse")
    val outerRingScale by infiniteTransition.animateFloat(
        initialValue  = 1f,
        targetValue   = 1.45f,
        animationSpec = infiniteRepeatable(tween(1100, easing = EaseOut), RepeatMode.Restart),
        label         = "outer_scale"
    )
    val outerRingAlpha by infiniteTransition.animateFloat(
        initialValue  = 0.4f,
        targetValue   = 0f,
        animationSpec = infiniteRepeatable(tween(1100, easing = EaseOut), RepeatMode.Restart),
        label         = "outer_alpha"
    )
    val innerPulse by infiniteTransition.animateFloat(
        initialValue  = 1f,
        targetValue   = 1.06f,
        animationSpec = infiniteRepeatable(tween(600, easing = EaseInOut), RepeatMode.Reverse),
        label         = "inner_pulse"
    )

    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(18.dp)
    ) {
        // Big button
        Box(
            modifier         = Modifier.size(160.dp),
            contentAlignment = Alignment.Center
        ) {
            // Outer pulse ring (only while recording)
            if (isRecording) {
                Box(
                    modifier = Modifier
                        .size(160.dp)
                        .scale(outerRingScale)
                        .background(Red500.copy(alpha = outerRingAlpha), CircleShape)
                )
            }

            // Glow ring
            Box(
                modifier = Modifier
                    .size(130.dp)
                    .background(
                        if (isRecording) Red500.copy(alpha = 0.15f)
                        else Teal500.copy(alpha = 0.15f),
                        CircleShape
                    )
            )

            // Main button
            Box(
                modifier = Modifier
                    .size(100.dp)
                    .scale(if (isRecording) innerPulse else 1f)
                    .background(
                        when {
                            isAnalyzing -> OnSurfaceMid
                            isRecording -> Red500
                            else        -> Teal500
                        },
                        CircleShape
                    )
                    .clickable(enabled = !isAnalyzing) {
                        if (isRecording) onStopRecording() else onStartRecording()
                    },
                contentAlignment = Alignment.Center
            ) {
                when {
                    isAnalyzing -> CircularProgressIndicator(
                        modifier   = Modifier.size(32.dp),
                        strokeWidth = 3.dp,
                        color      = Color.White
                    )
                    isRecording -> Box(
                        modifier = Modifier
                            .size(28.dp)
                            .background(Color.White, RoundedCornerShape(6.dp))
                    )
                    else -> Icon(
                        Icons.Filled.Mic,
                        contentDescription = "Ghi âm",
                        tint     = Color.White,
                        modifier = Modifier.size(40.dp)
                    )
                }
            }
        }

        // Status text
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Text(
                when {
                    isAnalyzing -> "Đang phân tích AI..."
                    isRecording -> "Đang ghi âm  •  ${uiState.recordingSeconds}s"
                    else        -> "Nhấn để ghi âm"
                },
                fontSize   = 18.sp,
                fontWeight = FontWeight.Bold,
                color      = Color.White
            )
            Text(
                when {
                    isAnalyzing -> "Mô hình TFLite đang xử lý"
                    isRecording -> "Nói rõ ràng vào microphone"
                    else        -> "Phân tích giọng nói bằng AI on-device"
                },
                fontSize = 13.sp,
                color    = Color.White.copy(alpha = 0.6f)
            )
        }

        // Secondary action when recording
        if (isRecording && !isAnalyzing) {
            OutlinedButton(
                onClick = onStopAndSaveSample,
                shape   = RoundedCornerShape(12.dp),
                colors  = ButtonDefaults.outlinedButtonColors(contentColor = Color.White.copy(alpha = 0.8f))
            ) {
                Icon(Icons.Filled.Storage, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(6.dp))
                Text("Dừng & Lưu Mẫu Dataset", fontSize = 13.sp)
            }
        }

        // Chips
        if (!isRecording && !isAnalyzing) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                MiniChip("On-Device AI", Teal400)
                MiniChip("TFLite",       Purple)
                MiniChip("Offline",      Green500)
            }
        }
    }
}

@Composable
private fun PermissionHeroCard(onRequestPermission: () -> Unit) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
        modifier            = Modifier.padding(horizontal = 24.dp)
    ) {
        Box(
            modifier         = Modifier
                .size(80.dp)
                .background(Orange500.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(Icons.Filled.Mic, contentDescription = null, tint = Orange500, modifier = Modifier.size(38.dp))
        }
        Text("Cần quyền Microphone", fontSize = 17.sp, fontWeight = FontWeight.Bold, color = Color.White)
        Text(
            "Ứng dụng cần quyền để thu âm và phân tích. Dữ liệu chỉ xử lý cục bộ, không gửi lên internet.",
            fontSize   = 13.sp,
            color      = Color.White.copy(alpha = 0.65f),
            textAlign  = TextAlign.Center,
            lineHeight = 20.sp
        )
        Button(
            onClick = onRequestPermission,
            colors  = ButtonDefaults.buttonColors(containerColor = Orange500),
            shape   = RoundedCornerShape(14.dp)
        ) {
            Icon(Icons.Filled.Mic, contentDescription = null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text("Cấp Quyền Microphone", fontWeight = FontWeight.Bold)
        }
    }
}

@Composable
private fun DetectEmptyHint() {
    Column(
        modifier            = Modifier
            .fillMaxWidth()
            .padding(vertical = 24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(8.dp)
    ) {
        Text("↑", fontSize = 28.sp, color = OnSurfaceLow)
        Text("Ghi âm để xem kết quả phân tích", fontSize = 14.sp, color = OnSurfaceMid, fontWeight = FontWeight.Medium)
        Text("Kết quả sẽ hiển thị ở đây sau khi phân tích xong", fontSize = 12.sp, color = OnSurfaceLow)
    }
}

// ─── Decision Card ────────────────────────────────────────────────────────────
@Composable
private fun DecisionResultCard(result: FusionDecisionResult) {
    var showInfo by remember { mutableStateOf(false) }

    val accent = when (result.decision) {
        AuthenticationDecision.ALLOW  -> Green500
        AuthenticationDecision.REVIEW -> Orange500
        AuthenticationDecision.BLOCK  -> Red500
    }
    val bg = when (result.decision) {
        AuthenticationDecision.ALLOW  -> GreenBg
        AuthenticationDecision.REVIEW -> OrangeBg
        AuthenticationDecision.BLOCK  -> RedBg
    }
    val emoji = when (result.decision) {
        AuthenticationDecision.ALLOW  -> "✓"
        AuthenticationDecision.REVIEW -> "?"
        AuthenticationDecision.BLOCK  -> "✕"
    }
    val headline = when (result.decision) {
        AuthenticationDecision.ALLOW  -> "Xác thực thành công"
        AuthenticationDecision.REVIEW -> "Cần kiểm tra lại"
        AuthenticationDecision.BLOCK  -> "Phát hiện giả mạo"
    }
    val sub = when (result.decision) {
        AuthenticationDecision.ALLOW  -> "ALLOW — Giọng nói hợp lệ"
        AuthenticationDecision.REVIEW -> "REVIEW — Kết quả không chắc chắn"
        AuthenticationDecision.BLOCK  -> "BLOCK — Nghi ngờ Deepfake / Replay"
    }

    Card(
        colors    = CardDefaults.cardColors(containerColor = bg),
        shape     = RoundedCornerShape(20.dp),
        elevation = CardDefaults.cardElevation(2.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment     = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Box(
                        modifier         = Modifier.size(52.dp).background(accent.copy(alpha = 0.15f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(emoji, fontSize = 22.sp, fontWeight = FontWeight.Black, color = accent)
                    }
                    Column {
                        Text(headline, fontSize = 19.sp, fontWeight = FontWeight.ExtraBold, color = accent)
                        Text(sub, fontSize = 12.sp, color = OnSurfaceMid)
                    }
                }
                IconButton(onClick = { showInfo = true }, modifier = Modifier.size(34.dp)) {
                    Icon(Icons.Filled.Info, contentDescription = null, tint = accent.copy(alpha = 0.6f))
                }
            }

            Text(result.reason, fontSize = 13.sp, color = OnSurfaceMid, lineHeight = 19.sp)

            HorizontalDivider(color = accent.copy(alpha = 0.15f))

            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                StatCell(label = "Spoof",   value = "${(result.spoofProbability * 100).toInt()}%", color = accent)
                StatCell(label = "ASV",     value = "%.2f".format(result.asvScore),               color = accent)
                StatCell(label = "Anti-spoof", value = if (result.meetsSpoofThreshold) "PASS" else "FAIL", color = accent)
                StatCell(label = "Speaker",    value = if (result.meetsAsvThreshold)   "PASS" else "FAIL", color = accent)
            }
        }
    }

    if (showInfo) {
        InfoDialog(
            title = "Quyết định xác thực",
            body  = "Hệ thống kết hợp 2 nguồn:\n\n▸ AI Anti-Spoof: phân tích 8 đặc trưng âm thanh, phát hiện giọng TTS/replay.\n▸ ASV: xác minh đúng người đăng ký.\n\nALLOW — Giọng thật + đúng người.\nREVIEW — Không chắc chắn, cần xem lại.\nBLOCK — Phát hiện giả mạo.",
            onDismiss = { showInfo = false }
        )
    }
}

@Composable
private fun StatCell(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(value, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold, color = color)
        Text(label, fontSize = 10.sp, color = OnSurfaceLow, textAlign = TextAlign.Center)
    }
}

// ─── Spoof Detail Card ────────────────────────────────────────────────────────
@Composable
private fun SpoofDetailCard(result: DetectionResult) {
    var showInfo by remember { mutableStateOf(false) }
    val accent = if (result.isSpoof) Red500 else Green500
    val label  = if (result.isSpoof) "SPOOF" else "BONAFIDE"
    val sub    = if (result.isSpoof) "Phát hiện giọng giả mạo" else "Giọng nói thật"

    val spoofAnim by animateFloatAsState(
        targetValue   = result.spoofProbability,
        animationSpec = tween(900, easing = EaseOut),
        label         = "spoof"
    )

    Card(
        colors    = CardDefaults.cardColors(containerColor = Surface1),
        shape     = RoundedCornerShape(20.dp),
        elevation = CardDefaults.cardElevation(1.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment     = Alignment.CenterVertically
            ) {
                Column {
                    Text("Kết quả AI Anti-Spoof", fontSize = 11.sp, color = OnSurfaceLow)
                    Row(
                        verticalAlignment     = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Box(
                            modifier         = Modifier.size(10.dp).background(accent, CircleShape)
                        )
                        Text(label, fontSize = 18.sp, fontWeight = FontWeight.ExtraBold, color = accent)
                        Text("·", fontSize = 18.sp, color = OnSurfaceLow)
                        Text(sub, fontSize = 13.sp, color = OnSurfaceMid, fontWeight = FontWeight.Medium)
                    }
                }
                IconButton(onClick = { showInfo = true }, modifier = Modifier.size(32.dp)) {
                    Icon(Icons.Filled.Info, contentDescription = null, tint = Teal500.copy(alpha = 0.7f))
                }
            }

            // Progress bar
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Row(
                    modifier              = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Xác suất giả mạo", fontSize = 12.sp, color = OnSurfaceMid)
                    Text(
                        "${(result.spoofProbability * 100).toInt()}%",
                        fontSize   = 15.sp,
                        fontWeight = FontWeight.ExtraBold,
                        color      = accent
                    )
                }
                LinearProgressIndicator(
                    progress   = { spoofAnim },
                    modifier   = Modifier.fillMaxWidth().height(12.dp).clip(RoundedCornerShape(6.dp)),
                    color      = accent,
                    trackColor = accent.copy(alpha = 0.12f),
                    strokeCap  = StrokeCap.Round
                )
                Row(
                    modifier              = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("0% Thật", fontSize = 10.sp, color = Green500)
                    Text("Ngưỡng ${"%.0f".format(result.threshold * 100)}%", fontSize = 10.sp, color = OnSurfaceLow)
                    Text("100% Giả", fontSize = 10.sp, color = Red500)
                }
            }

            HorizontalDivider(color = Surface0)

            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                MetricPill("Độ tin cậy", "${(result.confidence * 100).toInt()}%", Teal500)
                MetricPill("Thời lượng", "${"%.1f".format(result.recordingDurationSec)}s", Purple)
                MetricPill("Engine", result.modelName, if (result.modelName.contains("tflite")) Green500 else Orange500)
            }
        }
    }

    if (showInfo) {
        InfoDialog(
            title = "Giải thích Anti-Spoof",
            body  = "Xác suất giả mạo > Ngưỡng → SPOOF (giả mạo)\nXác suất ≤ Ngưỡng → BONAFIDE (thật)\n\nĐộ tin cậy: mô hình 'chắc chắn' đến mức nào.\n\nEngine TFLite = mô hình AI chính thức.\nHeuristic = fallback khi chưa có model.",
            onDismiss = { showInfo = false }
        )
    }
}

// ─── Features Card ────────────────────────────────────────────────────────────
@Composable
private fun FeaturesCard(result: DetectionResult) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        colors = CardDefaults.cardColors(containerColor = PurpleBg),
        shape  = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier              = Modifier.fillMaxWidth().clickable { expanded = !expanded },
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment     = Alignment.CenterVertically
            ) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Box(
                        modifier         = Modifier.size(34.dp).background(Purple.copy(alpha = 0.15f), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Text("8", fontSize = 14.sp, fontWeight = FontWeight.ExtraBold, color = Purple)
                    }
                    Column {
                        Text("Đặc trưng âm thanh", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF3D2B6B))
                        Text(if (expanded) "Thu gọn" else "Nhấn để xem chi tiết", fontSize = 11.sp, color = OnSurfaceLow)
                    }
                }
                Icon(
                    if (expanded) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown,
                    contentDescription = null, tint = Purple
                )
            }

            AnimatedVisibility(visible = expanded, enter = expandVertically(), exit = shrinkVertically()) {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    HorizontalDivider(color = Purple.copy(alpha = 0.15f))
                    listOf(
                        Triple("RMS",           "Root Mean Square",    "Năng lượng trung bình. Giọng TTS thường có RMS ổn định bất thường."),
                        Triple("Mean Abs",       "Biên độ trung bình",  "Giá trị tuyệt đối trung bình. Liên quan đến âm lượng tổng thể."),
                        Triple("ZCR",            "Zero Crossing Rate",  "Tần suất tín hiệu đổi dấu. TTS có ZCR khác giọng người thật."),
                        Triple("Peak",           "Đỉnh biên độ",        "Giá trị lớn nhất. Phát hiện clipping hoặc replay attack."),
                        Triple("Crest Factor",   "Hệ số đỉnh",          "Tỉ lệ đỉnh/RMS. Phản ánh cấu trúc động của tín hiệu."),
                        Triple("Clipping Ratio", "Tỉ lệ bão hoà",       "Tỷ lệ mẫu >98% biên độ. Dấu hiệu replay qua loa ngoài."),
                        Triple("Dynamic Range",  "Dải động",            "Khoảng max − min. Giọng thật có dải động tự nhiên hơn."),
                        Triple("Duration",       "Thời lượng",          "Độ dài đoạn âm thanh (giây). Ảnh hưởng độ tin cậy đặc trưng.")
                    ).forEach { (short, eng, desc) ->
                        Row(
                            horizontalArrangement = Arrangement.spacedBy(10.dp),
                            verticalAlignment     = Alignment.Top
                        ) {
                            Surface(shape = RoundedCornerShape(6.dp), color = Purple.copy(alpha = 0.15f)) {
                                Text(
                                    short,
                                    modifier   = Modifier.padding(horizontal = 6.dp, vertical = 3.dp),
                                    fontSize   = 10.sp,
                                    fontWeight = FontWeight.Bold,
                                    color      = Color(0xFF5E35B1)
                                )
                            }
                            Column(modifier = Modifier.weight(1f)) {
                                Text(eng, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, color = Color(0xFF3D2B6B))
                                Text(desc, fontSize = 11.sp, color = OnSurfaceMid, lineHeight = 16.sp)
                            }
                        }
                    }
                }
            }
        }
    }
}

// ─── Error Banner ─────────────────────────────────────────────────────────────
@Composable
private fun ErrorBanner(message: String, onDismiss: () -> Unit) {
    Card(colors = CardDefaults.cardColors(containerColor = RedBg), shape = RoundedCornerShape(14.dp)) {
        Row(
            modifier              = Modifier.padding(14.dp).fillMaxWidth(),
            verticalAlignment     = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(Icons.Filled.Warning, contentDescription = null, tint = Red500, modifier = Modifier.size(20.dp))
            Text(message, color = Color(0xFF7A0000), fontSize = 13.sp, modifier = Modifier.weight(1f), lineHeight = 18.sp)
            TextButton(onClick = onDismiss, contentPadding = androidx.compose.foundation.layout.PaddingValues(4.dp)) {
                Text("✕", color = Red500, fontWeight = FontWeight.Bold)
            }
        }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
//  TAB 2 — LỊCH SỬ
// ══════════════════════════════════════════════════════════════════════════════
@Composable
private fun HistoryTab(
    sessions: List<DetectionSession>,
    isExporting: Boolean = false,
    lastExportPath: String? = null,
    onExportCsv: () -> Unit = {},
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Surface0)
    ) {
        // Header
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Brush.verticalGradient(listOf(Navy800, Navy700)))
                .padding(start = 20.dp, end = 20.dp, top = 24.dp, bottom = 20.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
                Row(
                    modifier              = Modifier.fillMaxWidth(),
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Row(
                        verticalAlignment     = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Icon(Icons.Filled.History, contentDescription = null, tint = Teal400, modifier = Modifier.size(20.dp))
                        Text("Lịch sử phát hiện", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
                    }
                    if (sessions.isNotEmpty()) {
                        Button(
                            onClick  = onExportCsv,
                            enabled  = !isExporting,
                            colors   = ButtonDefaults.buttonColors(containerColor = Teal500.copy(alpha = 0.8f)),
                            shape    = RoundedCornerShape(10.dp),
                            contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 6.dp)
                        ) {
                            if (isExporting) {
                                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = Color.White)
                            } else {
                                Icon(Icons.Filled.Download, contentDescription = null, modifier = Modifier.size(15.dp))
                            }
                            Spacer(Modifier.width(5.dp))
                            Text(if (isExporting) "Đang xuất..." else "Xuất CSV", fontSize = 12.sp, fontWeight = FontWeight.SemiBold)
                        }
                    }
                }

                if (sessions.isNotEmpty()) {
                    val allowCount  = sessions.count { it.fusionDecision.decision == AuthenticationDecision.ALLOW }
                    val blockCount  = sessions.count { it.fusionDecision.decision == AuthenticationDecision.BLOCK }
                    val reviewCount = sessions.count { it.fusionDecision.decision == AuthenticationDecision.REVIEW }

                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        HistoryStatChip("${sessions.size} phiên", Teal400,   Teal500.copy(alpha = 0.2f))
                        HistoryStatChip("$allowCount ALLOW",   Green500,  Green500.copy(alpha = 0.18f))
                        if (reviewCount > 0)
                            HistoryStatChip("$reviewCount REVIEW", Orange500, Orange500.copy(alpha = 0.18f))
                        if (blockCount > 0)
                            HistoryStatChip("$blockCount BLOCK",   Red500,    Red500.copy(alpha = 0.18f))
                    }
                }
            }
        }

        lastExportPath?.let { path ->
            Card(
                colors    = CardDefaults.cardColors(containerColor = GreenBg),
                shape     = RoundedCornerShape(12.dp),
                modifier  = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            ) {
                Row(
                    modifier              = Modifier.padding(12.dp).fillMaxWidth(),
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Icon(Icons.Filled.CheckCircle, contentDescription = null, tint = Green500, modifier = Modifier.size(18.dp))
                    Column(modifier = Modifier.weight(1f)) {
                        Text("Xuất CSV thành công!", fontSize = 12.sp, fontWeight = FontWeight.Bold, color = Green500)
                        Text(path, fontSize = 10.sp, color = OnSurfaceMid, lineHeight = 14.sp)
                    }
                }
            }
        }

        if (sessions.isEmpty()) {
            Box(
                modifier         = Modifier.fillMaxSize(),
                contentAlignment = Alignment.Center
            ) {
                Column(
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Icon(Icons.Filled.History, contentDescription = null, tint = OnSurfaceLow, modifier = Modifier.size(56.dp))
                    Text("Chưa có phiên nào", fontSize = 16.sp, fontWeight = FontWeight.SemiBold, color = OnSurfaceMid)
                    Text("Chuyển sang tab Phát hiện để bắt đầu", fontSize = 13.sp, color = OnSurfaceLow)
                }
            }
        } else {
            LazyColumn(
                modifier            = Modifier.fillMaxSize(),
                contentPadding      = androidx.compose.foundation.layout.PaddingValues(16.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                itemsIndexed(sessions.reversed()) { idx, session ->
                    SessionCard(number = sessions.size - idx, session = session)
                }
            }
        }
    }
}

@Composable
private fun HistoryStatChip(text: String, textColor: Color, bgColor: Color) {
    Surface(shape = RoundedCornerShape(20.dp), color = bgColor) {
        Text(
            text,
            modifier   = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
            fontSize   = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color      = textColor
        )
    }
}

@Composable
private fun SessionCard(number: Int, session: DetectionSession) {
    val decision = session.fusionDecision.decision
    val accent   = when (decision) {
        AuthenticationDecision.ALLOW  -> Green500
        AuthenticationDecision.REVIEW -> Orange500
        AuthenticationDecision.BLOCK  -> Red500
    }
    val bg = when (decision) {
        AuthenticationDecision.ALLOW  -> GreenBg
        AuthenticationDecision.REVIEW -> OrangeBg
        AuthenticationDecision.BLOCK  -> RedBg
    }
    val icon = when (decision) {
        AuthenticationDecision.ALLOW  -> Icons.Filled.CheckCircle
        AuthenticationDecision.REVIEW -> Icons.Filled.Info
        AuthenticationDecision.BLOCK  -> Icons.Filled.Warning
    }
    val label = when (decision) {
        AuthenticationDecision.ALLOW  -> "ALLOW"
        AuthenticationDecision.REVIEW -> "REVIEW"
        AuthenticationDecision.BLOCK  -> "BLOCK"
    }

    Card(
        colors = CardDefaults.cardColors(containerColor = Surface1),
        shape  = RoundedCornerShape(14.dp),
        elevation = CardDefaults.cardElevation(0.5.dp)
    ) {
        Row(modifier = Modifier.fillMaxWidth()) {
            // Left color bar
            Box(modifier = Modifier.width(4.dp).height(72.dp).background(accent))
            Row(
                modifier              = Modifier.padding(horizontal = 14.dp, vertical = 12.dp).fillMaxWidth(),
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Box(
                    modifier         = Modifier.size(40.dp).background(accent.copy(alpha = 0.12f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(20.dp))
                }
                Column(modifier = Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Row(
                        verticalAlignment     = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Surface(shape = RoundedCornerShape(6.dp), color = accent.copy(alpha = 0.12f)) {
                            Text(
                                label,
                                modifier   = Modifier.padding(horizontal = 7.dp, vertical = 2.dp),
                                fontSize   = 11.sp,
                                fontWeight = FontWeight.ExtraBold,
                                color      = accent
                            )
                        }
                        Text("#$number", fontSize = 12.sp, color = OnSurfaceLow)
                    }
                    Text(
                        "Spoof ${"%.0f".format(session.detectionResult.spoofProbability * 100)}%  ·  " +
                        "ASV ${"%.2f".format(session.fusionDecision.asvScore)}  ·  " +
                        "${"%.1f".format(session.detectionResult.recordingDurationSec)}s",
                        fontSize = 12.sp, color = OnSurfaceMid
                    )
                }
                Text(formatTime(session.createdAtEpochMs), fontSize = 11.sp, color = OnSurfaceLow)
            }
        }
    }
}

// ══════════════════════════════════════════════════════════════════════════════
//  TAB 3 — CÀI ĐẶT
// ══════════════════════════════════════════════════════════════════════════════
@Composable
private fun SettingsTab(
    uiState: DetectorUiState,
    onAsvScoreInputChange: (String) -> Unit,
    onSpoofThresholdChange: (Float) -> Unit,
    onAsvThresholdChange: (Float) -> Unit,
    onUseRemoteAsvChange: (Boolean) -> Unit,
    onAsvEndpointChange: (String) -> Unit,
    onDatasetLabelChange: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .fillMaxSize()
            .background(Surface0)
    ) {
        // Header
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Brush.verticalGradient(listOf(Navy800, Navy700)))
                .padding(start = 20.dp, end = 20.dp, top = 24.dp, bottom = 20.dp)
        ) {
            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Row(
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(Icons.Filled.Settings, contentDescription = null, tint = Teal400, modifier = Modifier.size(20.dp))
                    Text("Cài đặt", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = Color.White)
                }
                Text("Ngưỡng · ASV · Dataset · Hướng dẫn", fontSize = 12.sp, color = Color.White.copy(alpha = 0.5f))
            }
        }

        Column(
            modifier            = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(20.dp)
        ) {
            // Model info
            ModelInfoCard()

            // Threshold settings
            SettingsSection(title = "PHÂN TÍCH") {
                ThresholdRow(
                    icon    = Icons.Filled.Shield,
                    label   = "Ngưỡng phát hiện giả mạo",
                    value   = "%.2f".format(uiState.spoofThreshold),
                    sub     = "Spoof Threshold — ranh giới BONAFIDE / SPOOF",
                    sliderVal      = uiState.spoofThreshold,
                    onSliderChange = onSpoofThresholdChange,
                    color   = Red500
                )
                HorizontalDivider(color = Surface0, thickness = 1.dp)
                ThresholdRow(
                    icon    = Icons.Filled.Person,
                    label   = "Ngưỡng xác minh người nói",
                    value   = "%.2f".format(uiState.asvThreshold),
                    sub     = "ASV Threshold — ngưỡng PASS / FAIL speaker",
                    sliderVal      = uiState.asvThreshold,
                    onSliderChange = onAsvThresholdChange,
                    color   = Teal500
                )
            }

            // ASV connection
            SettingsSection(title = "KẾT NỐI ASV") {
                Row(
                    modifier              = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment     = Alignment.CenterVertically
                ) {
                    Row(
                        verticalAlignment     = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Icon(Icons.Filled.Link, contentDescription = null, tint = Teal500, modifier = Modifier.size(20.dp))
                        Column {
                            Text("Dùng ASV Backend từ xa", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = OnSurface)
                            Text("Kết nối server xác minh danh tính", fontSize = 11.sp, color = OnSurfaceMid)
                        }
                    }
                    Switch(
                        checked         = if (uiState.strictReleaseMode) true else uiState.useRemoteAsv,
                        onCheckedChange  = onUseRemoteAsvChange,
                        enabled         = !uiState.strictReleaseMode
                    )
                }
                OutlinedTextField(
                    value          = uiState.asvEndpoint,
                    onValueChange  = onAsvEndpointChange,
                    label          = { Text("Endpoint ASV Server") },
                    placeholder    = { Text("https://your-server/api/asv/score") },
                    modifier       = Modifier.fillMaxWidth(),
                    singleLine     = true,
                    supportingText = { Text("Để trống nếu chỉ dùng AI offline", fontSize = 11.sp) }
                )
                if (!uiState.strictReleaseMode) {
                    OutlinedTextField(
                        value          = uiState.asvScoreInput,
                        onValueChange  = onAsvScoreInputChange,
                        label          = { Text("Điểm ASV thủ công (debug)") },
                        modifier       = Modifier.fillMaxWidth(),
                        singleLine     = true,
                        supportingText = { Text("0.0 – 1.0, chỉ dùng khi không có ASV server", fontSize = 11.sp) }
                    )
                }
                Surface(shape = RoundedCornerShape(8.dp), color = TealBg) {
                    Text(
                        "ASV: ${uiState.lastAsvSource} · Độ trễ: ${uiState.lastAsvLatencyMs}ms",
                        modifier   = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
                        fontSize   = 11.sp,
                        color      = Teal500
                    )
                }
            }

            // Dataset
            SettingsSection(title = "THU THẬP DỮ LIỆU") {
                DatasetCaptureContent(uiState = uiState, onDatasetLabelChange = onDatasetLabelChange)
            }

            // Guide
            SettingsSection(title = "TÀI LIỆU") {
                CollapsibleItem(
                    icon  = Icons.Filled.Info,
                    title = "Hướng dẫn sử dụng",
                    sub   = "3 bước cơ bản để phân tích giọng nói"
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        HorizontalDivider(color = Surface0)
                        listOf(
                            Triple("1", "Nhấn nút Ghi Âm",      "Nói rõ ràng vào mic trong 2–5 giây."),
                            Triple("2", "Nhấn Dừng & Phân Tích", "AI trích xuất 8 đặc trưng rồi phân loại."),
                            Triple("3", "Đọc kết quả",           "BONAFIDE/SPOOF + ALLOW/REVIEW/BLOCK.")
                        ).forEach { (n, t, d) ->
                            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                                Box(
                                    modifier         = Modifier.size(28.dp).background(Teal500, CircleShape),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Text(n, color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                                }
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(t, fontWeight = FontWeight.SemiBold, fontSize = 13.sp, color = OnSurface)
                                    Text(d, fontSize = 12.sp, color = OnSurfaceMid, lineHeight = 17.sp)
                                }
                            }
                        }
                    }
                }

                HorizontalDivider(color = Surface0)

                CollapsibleItem(
                    icon  = Icons.Filled.Info,
                    title = "Bảng thuật ngữ",
                    sub   = "12 khái niệm kỹ thuật được giải thích"
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        HorizontalDivider(color = Surface0)
                        listOf(
                            "Deepfake Voice"   to "Giọng nói tạo bởi AI, giả mạo giọng người thật với độ chân thực cao.",
                            "TTS"              to "Text-to-Speech — Chuyển văn bản thành giọng nói tổng hợp.",
                            "Voice Conversion" to "Chuyển đặc trưng giọng người này sang người khác.",
                            "Replay Attack"    to "Phát lại bản ghi âm giọng thật để đánh lừa hệ thống.",
                            "MFCC"             to "Mel-Frequency Cepstral Coefficients — đặc trưng xử lý tiếng nói.",
                            "Anti-Spoof / CM"  to "Countermeasure — hệ thống chống giả mạo giọng nói.",
                            "ASV"              to "Automatic Speaker Verification — xác minh danh tính người nói.",
                            "TFLite / LiteRT"  to "TensorFlow Lite — AI nhẹ chạy trực tiếp trên thiết bị.",
                            "EER"              to "Equal Error Rate — chỉ số đánh giá hệ thống (càng thấp càng tốt).",
                            "Edge AI"          to "AI chạy trên thiết bị, không gửi dữ liệu lên server.",
                            "Bonafide"         to "Giọng nói thật, thu âm trực tiếp từ người nói.",
                            "Spoof"            to "Giọng giả mạo — TTS, Voice Conversion, hoặc replay."
                        ).forEach { (term, def) ->
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Box(
                                    modifier         = Modifier.size(6.dp).offset(y = 5.dp).background(Green500, CircleShape)
                                )
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(term, fontWeight = FontWeight.SemiBold, fontSize = 12.sp, color = OnSurface)
                                    Text(def,  fontSize = 11.sp, color = OnSurfaceMid, lineHeight = 16.sp)
                                }
                            }
                        }
                    }
                }
            }

            // About
            AboutCard()

            Spacer(Modifier.height(8.dp))
        }
    }
}

// ─── About Card ───────────────────────────────────────────────────────────────
@Composable
private fun AboutCard() {
    Card(
        colors    = CardDefaults.cardColors(containerColor = Navy700),
        shape     = RoundedCornerShape(18.dp)
    ) {
        Column(modifier = Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {

            // App identity
            Row(
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(14.dp)
            ) {
                Box(
                    modifier         = Modifier
                        .size(56.dp)
                        .background(
                            Brush.radialGradient(listOf(Teal400.copy(alpha = 0.3f), Color.Transparent)),
                            CircleShape
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    Box(
                        modifier         = Modifier.size(44.dp).background(Teal500, CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(Icons.Filled.Shield, contentDescription = null, tint = Color.White, modifier = Modifier.size(24.dp))
                    }
                }
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("VoiceGuard", fontSize = 20.sp, fontWeight = FontWeight.ExtraBold, color = Color.White)
                    Text("Deepfake Voice Detection", fontSize = 12.sp, color = Teal400)
                    Text("Phiên bản 1.0.0  ·  TFLite On-Device", fontSize = 11.sp, color = Color.White.copy(alpha = 0.4f))
                }
            }

            HorizontalDivider(color = Color.White.copy(alpha = 0.08f))

            // Thesis info
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    "THÔNG TIN LUẬN VĂN",
                    fontSize      = 10.sp,
                    fontWeight    = FontWeight.Bold,
                    color         = Teal400,
                    letterSpacing = 0.8.sp
                )
                AboutRow(label = "Đề tài",   value = "Nghiên cứu giải pháp phát hiện giả mạo giọng nói (Deepfake Voice Detection) sử dụng AI tích hợp trên thiết bị Android")
                AboutRow(label = "Học viên", value = "Nguyễn Kim Ngân  ·  CHAT10")
                AboutRow(label = "GVHD",     value = "TS. Mai Đức Thọ")
                AboutRow(label = "Đơn vị",   value = "Học viện Kỹ thuật Mật mã (HVKTMM)")
                AboutRow(label = "Năm",      value = "2025–2026")
            }

            HorizontalDivider(color = Color.White.copy(alpha = 0.08f))

            // Tech stack
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "CÔNG NGHỆ",
                    fontSize      = 10.sp,
                    fontWeight    = FontWeight.Bold,
                    color         = Teal400,
                    letterSpacing = 0.8.sp
                )
                Row(
                    modifier              = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    TechChip("Kotlin / Compose")
                    TechChip("TFLite / LiteRT")
                    TechChip("DNN 8-feature")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    TechChip("VIVOS Dataset")
                    TechChip("mc_thu_hue Spoof")
                    TechChip("Edge AI")
                }
            }

            // Model performance
            HorizontalDivider(color = Color.White.copy(alpha = 0.08f))
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                AboutMetric("98.2%", "Accuracy")
                AboutMetric("0.982", "F1 Score")
                AboutMetric("1.93%", "EER")
                AboutMetric("0.997", "AUC")
            }
        }
    }
}

@Composable
private fun AboutRow(label: String, value: String) {
    Row(
        modifier          = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        Text(
            label,
            fontSize   = 11.sp,
            color      = Color.White.copy(alpha = 0.4f),
            modifier   = Modifier.width(68.dp)
        )
        Text(
            value,
            fontSize   = 12.sp,
            color      = Color.White.copy(alpha = 0.85f),
            modifier   = Modifier.weight(1f),
            lineHeight = 17.sp
        )
    }
}

@Composable
private fun TechChip(text: String) {
    Surface(shape = RoundedCornerShape(8.dp), color = Color.White.copy(alpha = 0.08f)) {
        Text(
            text,
            modifier   = Modifier.padding(horizontal = 9.dp, vertical = 4.dp),
            fontSize   = 11.sp,
            fontWeight = FontWeight.Medium,
            color      = Teal400
        )
    }
}

@Composable
private fun AboutMetric(value: String, label: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(value, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold, color = Green500)
        Text(label, fontSize = 10.sp, color = Color.White.copy(alpha = 0.4f))
    }
}

@Composable
private fun ModelInfoCard() {
    Card(
        colors = CardDefaults.cardColors(containerColor = Navy700),
        shape  = RoundedCornerShape(18.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(
                verticalAlignment     = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Box(
                    modifier         = Modifier.size(38.dp).background(Teal500.copy(alpha = 0.2f), CircleShape),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(Icons.Filled.Shield, contentDescription = null, tint = Teal400, modifier = Modifier.size(20.dp))
                }
                Column {
                    Text("Mô hình AI hiện tại", fontSize = 11.sp, color = Color.White.copy(alpha = 0.5f))
                    Text("voice_spoof_detector.tflite", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color.White)
                }
            }
            HorizontalDivider(color = Color.White.copy(alpha = 0.08f))
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                ModelMetric("Accuracy",  "98.2%",  Teal400)
                ModelMetric("F1 Score",  "0.982",  Green500)
                ModelMetric("Precision", "98.1%",  Purple)
                ModelMetric("Recall",    "98.4%",  Orange500)
            }
            Text(
                "Dataset: VIVOS (12,420 bonafide) + mc_thu_hue_fix_char (12,420 spoof)",
                fontSize = 11.sp, color = Color.White.copy(alpha = 0.4f), textAlign = TextAlign.Center,
                modifier = Modifier.fillMaxWidth()
            )
        }
    }
}

@Composable
private fun ModelMetric(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(value, fontSize = 15.sp, fontWeight = FontWeight.ExtraBold, color = color)
        Text(label, fontSize = 10.sp, color = Color.White.copy(alpha = 0.4f))
    }
}

@Composable
private fun SettingsSection(title: String, content: @Composable ColumnScope.() -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Text(
            title,
            fontSize      = 11.sp,
            fontWeight    = FontWeight.Bold,
            color         = Teal500,
            letterSpacing = 0.8.sp,
            modifier      = Modifier.padding(horizontal = 4.dp, vertical = 4.dp)
        )
        Card(
            colors    = CardDefaults.cardColors(containerColor = Surface1),
            shape     = RoundedCornerShape(16.dp),
            elevation = CardDefaults.cardElevation(0.5.dp)
        ) {
            Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                content()
            }
        }
    }
}

@Composable
private fun ThresholdRow(
    icon: ImageVector,
    label: String,
    value: String,
    sub: String,
    sliderVal: Float,
    onSliderChange: (Float) -> Unit,
    color: Color
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(
            verticalAlignment     = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(20.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(label, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = OnSurface)
                Text(sub, fontSize = 11.sp, color = OnSurfaceMid)
            }
            Surface(shape = RoundedCornerShape(8.dp), color = color.copy(alpha = 0.1f)) {
                Text(
                    value,
                    modifier   = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                    fontSize   = 14.sp,
                    fontWeight = FontWeight.ExtraBold,
                    color      = color
                )
            }
        }
        Slider(
            value         = sliderVal,
            onValueChange = onSliderChange,
            valueRange    = 0.05f..0.95f,
            modifier      = Modifier.padding(horizontal = 4.dp)
        )
    }
}

@Composable
private fun CollapsibleItem(
    icon: ImageVector,
    title: String,
    sub: String,
    content: @Composable ColumnScope.() -> Unit
) {
    var expanded by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            modifier              = Modifier.fillMaxWidth().clickable { expanded = !expanded },
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment     = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                Icon(icon, contentDescription = null, tint = Teal500, modifier = Modifier.size(20.dp))
                Column {
                    Text(title, fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = OnSurface)
                    Text(sub, fontSize = 11.sp, color = OnSurfaceMid)
                }
            }
            Icon(
                if (expanded) Icons.Filled.KeyboardArrowUp else Icons.Filled.KeyboardArrowDown,
                contentDescription = null, tint = OnSurfaceLow
            )
        }
        AnimatedVisibility(visible = expanded, enter = expandVertically(), exit = shrinkVertically()) {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                content()
            }
        }
    }
}

@Composable
private fun DatasetCaptureContent(
    uiState: DetectorUiState,
    onDatasetLabelChange: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(Icons.Filled.Storage, contentDescription = null, tint = Teal500, modifier = Modifier.size(20.dp))
            Column {
                Text("Thu thập Dataset", fontSize = 13.sp, fontWeight = FontWeight.SemiBold, color = OnSurface)
                Text("Ghi âm có nhãn để huấn luyện mô hình", fontSize = 11.sp, color = OnSurfaceMid)
            }
        }
        Text(
            "Chọn nhãn → Bắt Đầu Ghi Âm → Dừng & Lưu Mẫu để lưu WAV có nhãn vào bộ nhớ.",
            fontSize = 12.sp, color = OnSurfaceMid, lineHeight = 18.sp
        )
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp), modifier = Modifier.fillMaxWidth()) {
            Button(
                onClick  = { onDatasetLabelChange("bonafide") },
                modifier = Modifier.weight(1f),
                colors   = ButtonDefaults.buttonColors(
                    containerColor = if (uiState.datasetLabel == "bonafide") Green500 else Surface0,
                    contentColor   = if (uiState.datasetLabel == "bonafide") Color.White else OnSurfaceMid
                ),
                shape = RoundedCornerShape(10.dp)
            ) {
                Text(
                    if (uiState.datasetLabel == "bonafide") "✓ BONAFIDE" else "BONAFIDE",
                    fontWeight = FontWeight.Bold, fontSize = 13.sp
                )
            }
            Button(
                onClick  = { onDatasetLabelChange("spoof") },
                modifier = Modifier.weight(1f),
                colors   = ButtonDefaults.buttonColors(
                    containerColor = if (uiState.datasetLabel == "spoof") Red500 else Surface0,
                    contentColor   = if (uiState.datasetLabel == "spoof") Color.White else OnSurfaceMid
                ),
                shape = RoundedCornerShape(10.dp)
            ) {
                Text(
                    if (uiState.datasetLabel == "spoof") "✓ SPOOF" else "SPOOF",
                    fontWeight = FontWeight.Bold, fontSize = 13.sp
                )
            }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricPill("Nhãn",    uiState.datasetLabel.uppercase(), Teal500)
            MetricPill("Bonafide", "${uiState.savedBonafideCount}", Green500)
            MetricPill("Spoof",   "${uiState.savedSpoofCount}",    Red500)
        }
        if (uiState.isSavingSample) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CircularProgressIndicator(modifier = Modifier.size(14.dp), strokeWidth = 2.dp, color = Teal500)
                Text("Đang lưu...", fontSize = 12.sp, color = Teal500)
            }
        }
        uiState.lastSavedSamplePath?.let {
            Text("Đã lưu: $it", style = MaterialTheme.typography.bodySmall, color = OnSurfaceLow)
        }
    }
}

// ─── Shared ───────────────────────────────────────────────────────────────────
@Composable
private fun MetricPill(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(label, fontSize = 10.sp, color = OnSurfaceLow, textAlign = TextAlign.Center)
        Surface(shape = RoundedCornerShape(8.dp), color = color.copy(alpha = 0.1f)) {
            Text(
                value,
                modifier   = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                fontSize   = 12.sp,
                fontWeight = FontWeight.SemiBold,
                color      = color
            )
        }
    }
}

@Composable
private fun MiniChip(text: String, color: Color) {
    Surface(shape = RoundedCornerShape(20.dp), color = color.copy(alpha = 0.18f)) {
        Text(
            text,
            modifier   = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
            fontSize   = 11.sp,
            fontWeight = FontWeight.SemiBold,
            color      = color
        )
    }
}

// ─── Performance Card ─────────────────────────────────────────────────────────
@Composable
private fun PerformanceCard(uiState: DetectorUiState) {
    var showInfo by remember { mutableStateOf(false) }

    Card(
        colors    = CardDefaults.cardColors(containerColor = Color(0xFFF0ECFF)),
        shape     = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(0.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment     = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment     = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(Icons.Filled.Speed, contentDescription = null, tint = Purple, modifier = Modifier.size(18.dp))
                    Text("Hiệu năng thực tế", fontSize = 13.sp, fontWeight = FontWeight.Bold, color = Color(0xFF3D2B6B))
                }
                IconButton(onClick = { showInfo = true }, modifier = Modifier.size(28.dp)) {
                    Icon(Icons.Filled.Info, contentDescription = null, tint = Purple.copy(alpha = 0.6f), modifier = Modifier.size(16.dp))
                }
            }
            Row(
                modifier              = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
                PerfMetric(
                    label = "Trích đặc trưng",
                    value = "${uiState.lastFeatureMs} ms",
                    color = Teal500
                )
                PerfMetric(
                    label = "TFLite inference",
                    value = "${uiState.lastInferenceMs} ms",
                    color = Purple
                )
                PerfMetric(
                    label = "Tổng pipeline",
                    value = "${uiState.lastTotalPipelineMs} ms",
                    color = Green500
                )
                PerfMetric(
                    label = "RAM (JVM)",
                    value = "${"%.1f".format(uiState.lastRamMb)} MB",
                    color = Orange500
                )
            }
        }
    }

    if (showInfo) {
        InfoDialog(
            title = "Hiệu năng on-device",
            body  = "Trích đặc trưng: thời gian tính 8 đặc trưng từ PCM audio.\n\nTFLite inference: thời gian model DNN chạy forward pass trên thiết bị.\n\nTổng pipeline: từ lúc bắt đầu phân tích đến có kết quả (gồm validation + feature + inference).\n\nRAM (JVM): bộ nhớ Java Heap đang sử dụng bởi app tại thời điểm phân tích.",
            onDismiss = { showInfo = false }
        )
    }
}

@Composable
private fun PerfMetric(label: String, value: String, color: Color) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(value, fontSize = 14.sp, fontWeight = FontWeight.ExtraBold, color = color)
        Text(label, fontSize = 9.sp, color = OnSurfaceLow, textAlign = TextAlign.Center)
    }
}

@Composable
private fun InfoDialog(title: String, body: String, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Filled.Info, contentDescription = null, tint = Teal500, modifier = Modifier.size(20.dp))
                Text(title, fontWeight = FontWeight.Bold, fontSize = 15.sp)
            }
        },
        text           = { Text(body, fontSize = 13.sp, lineHeight = 20.sp, color = OnSurfaceMid) },
        confirmButton  = {
            TextButton(onClick = onDismiss) { Text("Đã hiểu", color = Teal500, fontWeight = FontWeight.Bold) }
        },
        containerColor = Color.White,
        shape          = RoundedCornerShape(20.dp)
    )
}

private fun formatTime(epochMs: Long): String =
    SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(Date(epochMs))
