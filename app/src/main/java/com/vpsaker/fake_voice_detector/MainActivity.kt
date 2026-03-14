package com.vpsaker.fake_voice_detector

import android.Manifest
import android.content.pm.ApplicationInfo
import android.content.pm.PackageManager
import android.os.Bundle
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
import com.vpsaker.fake_voice_detector.data.asv.HttpAsvScoreRepository
import com.vpsaker.fake_voice_detector.data.detection.AudioFeatureExtractor
import com.vpsaker.fake_voice_detector.data.detection.TFLiteSpoofDetectorEngine
import com.vpsaker.fake_voice_detector.data.detection.VoiceSpoofingRepositoryImpl
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
                    context = applicationContext,
                    allowHeuristicFallback = isDebugBuild
                )
            ),
            securityConfigRepository = SecurityConfigDataStoreRepository(applicationContext),
            asvScoreRepository = HttpAsvScoreRepository(),
            telemetryRepository = FileTelemetryRepository(applicationContext),
            strictReleaseMode = !isDebugBuild
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

                val uiState by viewModel.uiState.collectAsStateWithLifecycle()

                VoiceDetectorScreen(
                    uiState = uiState,
                    hasAudioPermission = hasAudioPermission,
                    onRequestPermission = {
                        permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                    },
                    onStartRecording = viewModel::startRecording,
                    onStopRecording = viewModel::stopAndAnalyze,
                    onAsvScoreInputChange = viewModel::updateAsvScoreInput,
                    onSpoofThresholdChange = viewModel::updateSpoofThreshold,
                    onAsvThresholdChange = viewModel::updateAsvThreshold,
                    onUseRemoteAsvChange = viewModel::updateUseRemoteAsv,
                    onAsvEndpointChange = viewModel::updateAsvEndpoint,
                    onDismissError = viewModel::dismissError,
                    modifier = Modifier.fillMaxSize()
                )
            }
        }
    }
}
