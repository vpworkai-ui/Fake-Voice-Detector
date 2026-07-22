package com.vpsaker.fake_voice_detector

import android.Manifest
import android.content.ContentResolver
import android.database.Cursor
import android.net.Uri
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Bundle
import android.provider.OpenableColumns
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.vpsaker.fake_voice_detector.data.audio.MicrophoneAudioRecorder
import com.vpsaker.fake_voice_detector.data.detection.AudioFeatureExtractor
import com.vpsaker.fake_voice_detector.data.detection.TFLiteSpoofDetectorEngine
import com.vpsaker.fake_voice_detector.data.detection.VoiceSpoofingRepositoryImpl
import com.vpsaker.fake_voice_detector.data.history.FileSessionHistoryStore
import com.vpsaker.fake_voice_detector.data.settings.SecurityConfigDataStoreRepository
import com.vpsaker.fake_voice_detector.data.telemetry.FileTelemetryRepository
import com.vpsaker.fake_voice_detector.presentation.VoiceDetectorScreen
import com.vpsaker.fake_voice_detector.presentation.VoiceDetectorViewModel
import com.vpsaker.fake_voice_detector.presentation.VoiceDetectorViewModelFactory
import com.vpsaker.fake_voice_detector.ui.theme.Fake_voice_detectorTheme

class MainActivity : ComponentActivity() {

    private val isDebugBuild: Boolean
        get() = (applicationInfo.flags and ApplicationInfo.FLAG_DEBUGGABLE) != 0

    private val viewModel: VoiceDetectorViewModel by viewModels {
        VoiceDetectorViewModelFactory(
            repository = VoiceSpoofingRepositoryImpl(
                recorder = MicrophoneAudioRecorder(),
                featureExtractor = AudioFeatureExtractor(),
                detectorEngine = TFLiteSpoofDetectorEngine(
                    context = applicationContext
                ),
                context = applicationContext
            ),
            securityConfigRepository = SecurityConfigDataStoreRepository(
                context = applicationContext
            ),
            telemetryRepository = FileTelemetryRepository(
                context = applicationContext,
                apiKey = BuildConfig.TELEMETRY_API_KEY
            ),
            sessionHistoryStore = FileSessionHistoryStore(
                context = applicationContext
            ),
            strictReleaseMode = !isDebugBuild,
            telemetryEndpointOverride = BuildConfig.TELEMETRY_ENDPOINT_DEFAULT
        )
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            Fake_voice_detectorTheme {
                var hasAudioPermission by remember {
                    mutableStateOf(
                        ContextCompat.checkSelfPermission(
                            this,
                            Manifest.permission.RECORD_AUDIO
                        ) == PackageManager.PERMISSION_GRANTED
                    )
                }

                val permissionLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.RequestPermission()
                ) { isGranted ->
                    hasAudioPermission = isGranted
                }

                val audioPickerLauncher = rememberLauncherForActivityResult(
                    contract = ActivityResultContracts.OpenDocument()
                ) { uri ->
                    uri ?: return@rememberLauncherForActivityResult
                    runCatching {
                        contentResolver.takePersistableUriPermission(
                            uri,
                            android.content.Intent.FLAG_GRANT_READ_URI_PERMISSION
                        )
                    }
                    val fileBytes = contentResolver.openInputStream(uri)?.use { it.readBytes() }
                    if (fileBytes == null) {
                        viewModel.showError("Khong the doc file audio da chon. Vui long thu lai voi file WAV hop le.")
                    } else {
                        viewModel.analyzeImportedAudio(
                            fileName = resolveDisplayName(contentResolver, uri),
                            data = fileBytes
                        )
                    }
                }

                val uiState by viewModel.uiState.collectAsStateWithLifecycle()

                VoiceDetectorScreen(
                    uiState = uiState,
                    hasAudioPermission = hasAudioPermission,
                    onRequestPermission = {
                        permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    },
                    onStartRecording = viewModel::startRecording,
                    onStopRecording = viewModel::stopAndAnalyze,
                    onStopAndSaveSample = viewModel::stopAndSaveSample,
                    onPickAudioFile = {
                        audioPickerLauncher.launch(arrayOf("audio/wav", "audio/x-wav", "audio/*"))
                    },
                    onSpoofThresholdChange = viewModel::updateSpoofThreshold,
                    onDatasetLabelChange = viewModel::updateDatasetLabel,
                    onDismissError = viewModel::dismissError,
                    onDeleteSession = viewModel::deleteSession,
                    onExportCsv = { viewModel.exportSessionsToCsv(applicationContext) },
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }

    private fun resolveDisplayName(contentResolver: ContentResolver, uri: Uri): String {
        val projection = arrayOf(OpenableColumns.DISPLAY_NAME)
        val cursor: Cursor? = contentResolver.query(uri, projection, null, null, null)
        cursor.use { c ->
            if (c != null && c.moveToFirst()) {
                val columnIndex = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                if (columnIndex >= 0) {
                    return c.getString(columnIndex) ?: "selected_audio.wav"
                }
            }
        }
        return uri.lastPathSegment ?: "selected_audio.wav"
    }
}
