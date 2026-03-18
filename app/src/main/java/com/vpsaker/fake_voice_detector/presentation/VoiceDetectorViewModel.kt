package com.vpsaker.fake_voice_detector.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.vpsaker.fake_voice_detector.core.DefaultDispatchersProvider
import com.vpsaker.fake_voice_detector.core.DispatchersProvider
import com.vpsaker.fake_voice_detector.domain.model.AsvScoreRequest
import com.vpsaker.fake_voice_detector.domain.model.AuthTelemetryEvent
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import com.vpsaker.fake_voice_detector.domain.repository.AsvScoreRepository
import com.vpsaker.fake_voice_detector.domain.repository.SecurityConfigRepository
import com.vpsaker.fake_voice_detector.domain.repository.TelemetryRepository
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import com.vpsaker.fake_voice_detector.domain.usecase.AnalyzeVoiceSpoofingUseCase
import com.vpsaker.fake_voice_detector.domain.usecase.FuseAuthenticationUseCase
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.net.URI

class VoiceDetectorViewModel(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val asvScoreRepository: AsvScoreRepository,
    private val telemetryRepository: TelemetryRepository,
    private val analyzeVoiceSpoofingUseCase: AnalyzeVoiceSpoofingUseCase,
    private val fuseAuthenticationUseCase: FuseAuthenticationUseCase,
    private val strictReleaseMode: Boolean,
    private val telemetryEndpointOverride: String,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow(DetectorUiState(strictReleaseMode = strictReleaseMode))
    val uiState: StateFlow<DetectorUiState> = _uiState.asStateFlow()

    private var recordTickerJob: Job? = null
    private var recordStartedAtMs: Long = 0L

    init {
        if (strictReleaseMode) {
            viewModelScope.launch(dispatchersProvider.io) {
                securityConfigRepository.updateUseRemoteAsv(true)
            }
        }
        observeConfig()
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
            val result = analyzeVoiceSpoofingUseCase()
            withContext(dispatchersProvider.main) {
                result
                    .onSuccess { detection ->
                        val current = _uiState.value
                        val patchedDetection = detection.copy(threshold = current.spoofThreshold)
                        val asvResolution = resolveAsvScore(current, patchedDetection.spoofProbability, patchedDetection.recordingDurationSec)
                            .getOrElse { throwable ->
                                _uiState.update {
                                    it.copy(
                                        isAnalyzing = false,
                                        errorMessage = throwable.message ?: "ASV resolution failed"
                                    )
                                }
                                return@onSuccess
                            }
                        val fusion = fuseAuthenticationUseCase(
                            spoofProbability = patchedDetection.spoofProbability,
                            asvScore = asvResolution.score,
                            config = SecurityConfig(
                                spoofThreshold = current.spoofThreshold,
                                asvThreshold = current.asvThreshold,
                                useRemoteAsv = current.useRemoteAsv,
                                asvEndpoint = current.asvEndpoint
                            )
                        )
                        val session = DetectionSession(
                            createdAtEpochMs = System.currentTimeMillis(),
                            detectionResult = patchedDetection,
                            fusionDecision = fusion
                        )

                        _uiState.update {
                            it.copy(
                                isAnalyzing = false,
                                result = patchedDetection,
                                fusionDecisionResult = fusion,
                                lastAsvSource = asvResolution.source,
                                lastAsvLatencyMs = asvResolution.latencyMs,
                                sessions = (listOf(session) + it.sessions).take(MAX_SESSION_HISTORY),
                                errorMessage = asvResolution.warning
                            )
                        }

                        logTelemetry(patchedDetection, fusion, asvResolution, current.asvEndpoint)
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

    fun updateAsvScoreInput(raw: String) {
        if (raw.length > 4) return
        if (raw.isNotEmpty() && !raw.matches(NUMBER_INPUT_REGEX)) return
        _uiState.update { it.copy(asvScoreInput = raw) }
    }

    fun updateSpoofThreshold(value: Float) {
        _uiState.update { it.copy(spoofThreshold = value.coerceIn(0.05f, 0.95f)) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateSpoofThreshold(value)
        }
    }

    fun updateAsvThreshold(value: Float) {
        _uiState.update { it.copy(asvThreshold = value.coerceIn(0.05f, 0.95f)) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateAsvThreshold(value)
        }
    }

    fun updateUseRemoteAsv(value: Boolean) {
        val safeValue = if (strictReleaseMode) true else value
        _uiState.update { it.copy(useRemoteAsv = safeValue) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateUseRemoteAsv(safeValue)
        }
    }

    fun updateAsvEndpoint(value: String) {
        _uiState.update { it.copy(asvEndpoint = value) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateAsvEndpoint(value)
        }
    }

    fun updateDatasetLabel(label: String) {
        val normalized = if (label.lowercase() == "spoof") "spoof" else "bonafide"
        _uiState.update { it.copy(datasetLabel = normalized) }
    }

    fun dismissError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    private fun observeConfig() {
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.configFlow.collect { config ->
                withContext(dispatchersProvider.main) {
                    _uiState.update {
                        val endpoint = config.asvEndpoint.trim()
                        val releaseEndpointError = if (strictReleaseMode && isPlaceholderEndpoint(endpoint)) {
                            "Release mode requires ASV_ENDPOINT to be configured (not example.com)."
                        } else {
                            null
                        }
                        it.copy(
                            spoofThreshold = config.spoofThreshold,
                            asvThreshold = config.asvThreshold,
                            useRemoteAsv = if (strictReleaseMode) true else config.useRemoteAsv,
                            asvEndpoint = endpoint,
                            errorMessage = releaseEndpointError ?: it.errorMessage
                        )
                    }
                }
            }
        }
    }

    private suspend fun resolveAsvScore(
        state: DetectorUiState,
        spoofProbability: Float,
        recordingDurationSec: Float
    ): Result<AsvResolution> {
        val manualScore = state.asvScoreInput.toFloatOrNull()?.coerceIn(0f, 1f) ?: DEFAULT_ASV_SCORE
        if (!state.useRemoteAsv || state.asvEndpoint.isBlank()) {
            if (strictReleaseMode) {
                return Result.failure(
                    IllegalStateException("Release mode requires remote ASV enabled and endpoint configured")
                )
            }
            return Result.success(AsvResolution(score = manualScore, source = "manual", latencyMs = 0L, warning = null))
        }

        val remote = asvScoreRepository.fetchAsvScore(
            AsvScoreRequest(
                endpoint = state.asvEndpoint,
                spoofProbability = spoofProbability,
                recordingDurationSec = recordingDurationSec,
                sessionTimestampMs = System.currentTimeMillis()
            )
        )

        return remote.fold(
            onSuccess = { result ->
                Result.success(
                    AsvResolution(score = result.score, source = result.source, latencyMs = result.latencyMs, warning = null)
                )
            },
            onFailure = { throwable ->
                if (strictReleaseMode) {
                    Result.failure(IllegalStateException("Remote ASV failed in release mode: ${throwable.message}", throwable))
                } else {
                    Result.success(
                        AsvResolution(
                            score = manualScore,
                            source = "manual-fallback",
                            latencyMs = 0L,
                            warning = "Remote ASV failed, fallback manual score: ${throwable.message}"
                        )
                    )
                }
            }
        )
    }

    private fun logTelemetry(
        detection: com.vpsaker.fake_voice_detector.domain.model.DetectionResult,
        fusion: com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult,
        asvResolution: AsvResolution,
        asvEndpoint: String
    ) {
        viewModelScope.launch(dispatchersProvider.io) {
            val event = AuthTelemetryEvent(
                timestampMs = System.currentTimeMillis(),
                spoofProbability = detection.spoofProbability,
                asvScore = fusion.asvScore,
                decision = fusion.decision.name,
                reason = fusion.reason,
                asvSource = asvResolution.source,
                asvLatencyMs = asvResolution.latencyMs,
                modelName = detection.modelName,
                recordingDurationSec = detection.recordingDurationSec
            )
            telemetryRepository.logAuthenticationEvent(
                event
            ).onFailure { throwable ->
                _uiState.update {
                    it.copy(telemetryStatus = "log-failed: ${throwable.message}")
                }
                return@launch
            }

            val telemetryEndpoint = deriveTelemetryEndpoint(asvEndpoint)
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

    private fun deriveTelemetryEndpoint(asvEndpoint: String): String? {
        if (telemetryEndpointOverride.isNotBlank()) return telemetryEndpointOverride.trim()
        if (asvEndpoint.isBlank()) return null
        return runCatching {
            val uri = URI(asvEndpoint.trim())
            val basePath = uri.path?.trimEnd('/').orEmpty()
            val telemetryPath = if (basePath.endsWith("/asv/score")) {
                basePath.removeSuffix("/asv/score") + "/telemetry/events"
            } else {
                "$basePath/telemetry/events"
            }.replace("//", "/")
            URI(uri.scheme, uri.authority, telemetryPath, null, null).toString()
        }.getOrNull()
    }

    private fun isPlaceholderEndpoint(endpoint: String): Boolean {
        if (endpoint.isBlank()) return true
        val normalized = endpoint.lowercase()
        return normalized.contains("example.com") || normalized.contains("localhost")
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

    private data class AsvResolution(
        val score: Float,
        val source: String,
        val latencyMs: Long,
        val warning: String?
    )

    private companion object {
        const val DEFAULT_ASV_SCORE = 0.5f
        const val MAX_SESSION_HISTORY = 10
        val NUMBER_INPUT_REGEX = Regex("^\\d*\\.?\\d*$")
    }
}

class VoiceDetectorViewModelFactory(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val asvScoreRepository: AsvScoreRepository,
    private val telemetryRepository: TelemetryRepository,
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
                asvScoreRepository = asvScoreRepository,
                telemetryRepository = telemetryRepository,
                analyzeVoiceSpoofingUseCase = AnalyzeVoiceSpoofingUseCase(repository),
                fuseAuthenticationUseCase = FuseAuthenticationUseCase(),
                strictReleaseMode = strictReleaseMode,
                telemetryEndpointOverride = telemetryEndpointOverride,
                dispatchersProvider = dispatchersProvider
            ) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
