package com.vpsaker.fake_voice_detector.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.vpsaker.fake_voice_detector.data.history.FileSessionHistoryStore
import com.vpsaker.fake_voice_detector.data.settings.SecurityConfigDataStoreRepository
import com.vpsaker.fake_voice_detector.core.DefaultDispatchersProvider
import com.vpsaker.fake_voice_detector.core.DispatchersProvider
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.repository.SecurityConfigRepository
import com.vpsaker.fake_voice_detector.domain.repository.TelemetryRepository
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import com.vpsaker.fake_voice_detector.domain.usecase.AnalyzeVoiceSpoofingUseCase
import com.vpsaker.fake_voice_detector.domain.usecase.EvaluateSpoofResultUseCase
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class VoiceDetectorViewModel(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val telemetryRepository: TelemetryRepository,
    private val sessionHistoryStore: FileSessionHistoryStore,
    private val analyzeVoiceSpoofingUseCase: AnalyzeVoiceSpoofingUseCase,
    private val evaluateSpoofResultUseCase: EvaluateSpoofResultUseCase,
    private val strictReleaseMode: Boolean,
    private val telemetryEndpointOverride: String,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow(DetectorUiState(strictReleaseMode = strictReleaseMode))
    val uiState: StateFlow<DetectorUiState> = _uiState.asStateFlow()

    private var recordTickerJob: Job? = null
    private var recordStartedAtMs: Long = 0L

    init {
        ensureConfigDefaults()
        observeConfig()
        loadPersistedSessions()
    }

    fun startRecording() {
        if (_uiState.value.isRecording || _uiState.value.isAnalyzing) return

        viewModelScope.launch(dispatchersProvider.io) {
            val startResult = repository.startRecording()
            withContext(dispatchersProvider.main) {
                startResult
                    .onSuccess {
                        recordStartedAtMs = System.currentTimeMillis()
                        _uiState.update {
                            it.copy(
                                isRecording = true,
                                recordingSeconds = 0,
                                errorMessage = null
                            )
                        }
                        startTicker()
                    }
                    .onFailure { throwable ->
                        _uiState.update {
                            it.copy(errorMessage = throwable.message ?: "Unable to start recording")
                        }
                    }
            }
        }
    }

    fun stopAndAnalyze() {
        if (!_uiState.value.isRecording || _uiState.value.isAnalyzing) return

        stopTicker()
        _uiState.update { it.copy(isRecording = false, isAnalyzing = true, errorMessage = null) }

        viewModelScope.launch(dispatchersProvider.io) {
            val pipelineStart = System.currentTimeMillis()
            val result = analyzeVoiceSpoofingUseCase()
            val pipelineMs = System.currentTimeMillis() - pipelineStart
            val ramMb = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1_048_576f
            withContext(dispatchersProvider.main) {
                result
                    .onSuccess { detection ->
                        val current = _uiState.value
                        val patchedDetection = detection.copy(threshold = current.spoofThreshold)
                        val fusion = evaluateSpoofResultUseCase(
                            spoofProbability = patchedDetection.spoofProbability,
                            spoofThreshold = current.spoofThreshold
                        )
                        val session = DetectionSession(
                            createdAtEpochMs = System.currentTimeMillis(),
                            detectionResult = patchedDetection,
                            fusionDecision = fusion
                        )

                        _uiState.update {
                            val updatedSessions = (listOf(session) + it.sessions).take(MAX_SESSION_HISTORY)
                            it.copy(
                                isAnalyzing = false,
                                result = patchedDetection,
                                fusionDecisionResult = fusion,
                                sessions = updatedSessions,
                                errorMessage = null,
                                lastTotalPipelineMs = pipelineMs,
                                lastInferenceMs = patchedDetection.inferenceMs,
                                lastFeatureMs = patchedDetection.featureExtractionMs,
                                lastRamMb = ramMb
                            )
                        }

                        persistCurrentSessions()

                        logTelemetry(patchedDetection, fusion)
                    }
                    .onFailure { throwable ->
                        _uiState.update {
                            it.copy(
                                isAnalyzing = false,
                                errorMessage = throwable.message ?: "Analysis failed"
                            )
                        }
                    }
            }
        }
    }

    fun analyzeImportedAudio(fileName: String, data: ByteArray) {
        if (_uiState.value.isRecording || _uiState.value.isAnalyzing) return

        _uiState.update {
            it.copy(
                isAnalyzing = true,
                errorMessage = null,
                lastImportedFileName = fileName
            )
        }

        viewModelScope.launch(dispatchersProvider.io) {
            val pipelineStart = System.currentTimeMillis()
            val result = repository.analyzeImportedAudio(fileName, data)
            val pipelineMs = System.currentTimeMillis() - pipelineStart
            val ramMb = (Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory()) / 1_048_576f
            withContext(dispatchersProvider.main) {
                result
                    .onSuccess { detection ->
                        val current = _uiState.value
                        val patchedDetection = detection.copy(threshold = current.spoofThreshold)
                        val fusion = evaluateSpoofResultUseCase(
                            spoofProbability = patchedDetection.spoofProbability,
                            spoofThreshold = current.spoofThreshold
                        )
                        val session = DetectionSession(
                            createdAtEpochMs = System.currentTimeMillis(),
                            detectionResult = patchedDetection,
                            fusionDecision = fusion
                        )

                        _uiState.update {
                            val updatedSessions = (listOf(session) + it.sessions).take(MAX_SESSION_HISTORY)
                            it.copy(
                                isAnalyzing = false,
                                result = patchedDetection,
                                fusionDecisionResult = fusion,
                                sessions = updatedSessions,
                                errorMessage = null,
                                lastTotalPipelineMs = pipelineMs,
                                lastInferenceMs = patchedDetection.inferenceMs,
                                lastFeatureMs = patchedDetection.featureExtractionMs,
                                lastRamMb = ramMb,
                                lastImportedFileName = fileName
                            )
                        }

                        persistCurrentSessions()

                        logTelemetry(patchedDetection, fusion)
                    }
                    .onFailure { throwable ->
                        _uiState.update {
                            it.copy(
                                isAnalyzing = false,
                                errorMessage = throwable.message ?: "Imported audio analysis failed",
                                lastImportedFileName = fileName
                            )
                        }
                    }
            }
        }
    }

    fun stopAndSaveSample() {
        if (!_uiState.value.isRecording || _uiState.value.isAnalyzing) return

        stopTicker()
        _uiState.update { it.copy(isRecording = false, isAnalyzing = true, isSavingSample = true, errorMessage = null) }

        viewModelScope.launch(dispatchersProvider.io) {
            val label = _uiState.value.datasetLabel
            val saveResult = repository.stopRecordingAndSaveSample(label)
            withContext(dispatchersProvider.main) {
                saveResult
                    .onSuccess { savedPath ->
                        _uiState.update {
                            val isSpoof = label == "spoof"
                            it.copy(
                                isAnalyzing = false,
                                isSavingSample = false,
                                lastSavedSamplePath = savedPath,
                                savedBonafideCount = if (!isSpoof) it.savedBonafideCount + 1 else it.savedBonafideCount,
                                savedSpoofCount = if (isSpoof) it.savedSpoofCount + 1 else it.savedSpoofCount,
                                errorMessage = null
                            )
                        }
                    }
                    .onFailure { throwable ->
                        _uiState.update {
                            it.copy(
                                isAnalyzing = false,
                                isSavingSample = false,
                                errorMessage = throwable.message ?: "Save dataset sample failed"
                            )
                        }
                    }
            }
        }
    }

    fun updateSpoofThreshold(value: Float) {
        val normalized = value.coerceIn(0.05f, 0.95f)
        _uiState.update { it.copy(spoofThreshold = normalized) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateSpoofThreshold(normalized)
        }
    }

    fun updateDatasetLabel(label: String) {
        val normalized = if (label.lowercase() == "spoof") "spoof" else "bonafide"
        _uiState.update { it.copy(datasetLabel = normalized) }
    }

    fun dismissError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    fun showError(message: String) {
        _uiState.update { it.copy(errorMessage = message) }
    }

    fun exportSessionsToCsv(context: android.content.Context) {
        val sessions = _uiState.value.sessions
        if (sessions.isEmpty()) return

        _uiState.update { it.copy(isExporting = true) }
        viewModelScope.launch(dispatchersProvider.io) {
            runCatching {
                val dir = context.getExternalFilesDir(null) ?: context.filesDir
                val ts  = java.text.SimpleDateFormat("yyyyMMdd_HHmmss", java.util.Locale.getDefault())
                    .format(java.util.Date())
                val file = java.io.File(dir, "VoiceGuard_results_$ts.csv")

                val header = "No,Thoi_gian,Quyet_dinh,Spoof_%,Tin_cay_%,Thoi_luong_s,Model,Feature_ms,Inference_ms,Pipeline_ms"
                val rows = sessions.reversed().mapIndexed { idx, s ->
                    listOf(
                        idx + 1,
                        java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss", java.util.Locale.getDefault())
                            .format(java.util.Date(s.createdAtEpochMs)),
                        s.fusionDecision.decision.name,
                        "%.2f".format(s.detectionResult.spoofProbability * 100),
                        "%.2f".format(s.detectionResult.confidence * 100),
                        "%.2f".format(s.detectionResult.recordingDurationSec),
                        s.detectionResult.modelName,
                        s.detectionResult.featureExtractionMs,
                        s.detectionResult.inferenceMs,
                        s.detectionResult.inferenceMs
                            + s.detectionResult.featureExtractionMs
                    ).joinToString(",")
                }
                file.writeText((listOf(header) + rows).joinToString("\n"), Charsets.UTF_8)
                file.absolutePath
            }.onSuccess { path ->
                withContext(dispatchersProvider.main) {
                    _uiState.update { it.copy(isExporting = false, lastExportPath = path) }
                }
            }.onFailure { err ->
                withContext(dispatchersProvider.main) {
                    _uiState.update {
                        it.copy(isExporting = false, errorMessage = "Xuất CSV thất bại: ${err.message}")
                    }
                }
            }
        }
    }

    fun deleteSession(session: DetectionSession) {
        _uiState.update { current ->
            current.copy(
                sessions = current.sessions.filterNot {
                    it.createdAtEpochMs == session.createdAtEpochMs && it == session
                }
            )
        }
        persistCurrentSessions()
    }

    private fun observeConfig() {
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.configFlow.collect { config ->
                withContext(dispatchersProvider.main) {
                    _uiState.update {
                        it.copy(
                            spoofThreshold = config.spoofThreshold,
                            errorMessage = it.errorMessage
                        )
                    }
                }
            }
        }
    }

    private fun ensureConfigDefaults() {
        val dataStoreRepository = securityConfigRepository as? SecurityConfigDataStoreRepository ?: return
        viewModelScope.launch(dispatchersProvider.io) {
            dataStoreRepository.ensureCurrentDefaults()
        }
    }

    private fun loadPersistedSessions() {
        viewModelScope.launch(dispatchersProvider.io) {
            val sessions = sessionHistoryStore.loadSessions()
                .sortedByDescending { it.createdAtEpochMs }
                .take(MAX_SESSION_HISTORY)
            withContext(dispatchersProvider.main) {
                _uiState.update { current -> current.copy(sessions = sessions) }
            }
        }
    }

    private fun persistCurrentSessions() {
        val snapshot = _uiState.value.sessions.take(MAX_SESSION_HISTORY)
        viewModelScope.launch(dispatchersProvider.io) {
            sessionHistoryStore.saveSessions(snapshot)
        }
    }

    private fun logTelemetry(
        detection: com.vpsaker.fake_voice_detector.domain.model.DetectionResult,
        fusion: com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult
    ) {
        viewModelScope.launch(dispatchersProvider.io) {
            val event = AuthTelemetryEvent(
                timestampMs = System.currentTimeMillis(),
                fileName = detection.inputMetadata.fileName,
                inputSource = detection.inputMetadata.inputSource,
                fileHash = detection.inputMetadata.fileHash,
                sampleRateHz = detection.inputMetadata.normalizedSampleRateHz,
                originalSampleRateHz = detection.inputMetadata.originalSampleRateHz,
                channelCount = detection.inputMetadata.channelCount,
                spoofProbability = detection.spoofProbability,
                threshold = fusion.spoofThreshold,
                predictedLabel = if (detection.isSpoof) "SPOOF" else "BONAFIDE",
                decision = fusion.decision.name,
                reason = fusion.reason,
                modelName = detection.modelName,
                recordingDurationSec = detection.recordingDurationSec,
                confidence = fusion.confidence,
                meetsSpoofThreshold = fusion.meetsSpoofThreshold,
                featureExtractionMs = detection.featureExtractionMs,
                inferenceMs = detection.inferenceMs,
                acousticFeatures = detection.acousticFeatures,
            )
            telemetryRepository.logAuthenticationEvent(
                event
            ).onFailure { throwable ->
                _uiState.update {
                    it.copy(telemetryStatus = "log-failed: ${throwable.message}")
                }
                return@launch
            }

            val telemetryEndpoint = deriveTelemetryEndpoint()
            if (telemetryEndpoint == null) {
                _uiState.update {
                    it.copy(telemetryStatus = "queued-local")
                }
                return@launch
            }

            telemetryRepository.flushPendingEvents(telemetryEndpoint)
                .onSuccess { flushedCount ->
                    _uiState.update {
                        it.copy(
                            lastTelemetryFlushCount = flushedCount,
                            telemetryStatus = if (flushedCount > 0) "synced" else "no-pending"
                        )
                    }
                }
                .onFailure { throwable ->
                    _uiState.update {
                        it.copy(telemetryStatus = "sync-failed: ${throwable.message}")
                    }
                }
        }
    }

    private fun deriveTelemetryEndpoint(): String? {
        if (telemetryEndpointOverride.isNotBlank()) return telemetryEndpointOverride.trim()
        return null
    }

    private fun startTicker() {
        recordTickerJob?.cancel()
        recordTickerJob = viewModelScope.launch(dispatchersProvider.main) {
            while (true) {
                val elapsed = ((System.currentTimeMillis() - recordStartedAtMs) / 1000L).toInt()
                _uiState.update { current ->
                    if (current.isRecording) current.copy(recordingSeconds = elapsed) else current
                }
                delay(250)
            }
        }
    }

    private fun stopTicker() {
        recordTickerJob?.cancel()
        recordTickerJob = null
    }

    override fun onCleared() {
        super.onCleared()
        stopTicker()
        if (repository.isRecording()) {
            viewModelScope.launch(dispatchersProvider.io) {
                repository.stopRecordingAndAnalyze()
            }
        }
    }

    private companion object {
        const val MAX_SESSION_HISTORY = 10
    }
}

class VoiceDetectorViewModelFactory(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val telemetryRepository: TelemetryRepository,
    private val sessionHistoryStore: FileSessionHistoryStore,
    private val strictReleaseMode: Boolean,
    private val telemetryEndpointOverride: String = "",
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModelProvider.Factory {

    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(VoiceDetectorViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return VoiceDetectorViewModel(
                repository = repository,
                securityConfigRepository = securityConfigRepository,
                telemetryRepository = telemetryRepository,
                sessionHistoryStore = sessionHistoryStore,
                analyzeVoiceSpoofingUseCase = AnalyzeVoiceSpoofingUseCase(repository),
                evaluateSpoofResultUseCase = EvaluateSpoofResultUseCase(),
                strictReleaseMode = strictReleaseMode,
                telemetryEndpointOverride = telemetryEndpointOverride,
                dispatchersProvider = dispatchersProvider
            ) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
