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

class VoiceDetectorViewModel(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val asvScoreRepository: AsvScoreRepository,
    private val telemetryRepository: TelemetryRepository,
    private val analyzeVoiceSpoofingUseCase: AnalyzeVoiceSpoofingUseCase,
    private val fuseAuthenticationUseCase: FuseAuthenticationUseCase,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow(DetectorUiState())
    val uiState: StateFlow<DetectorUiState> = _uiState.asStateFlow()

    private var recordTickerJob: Job? = null
    private var recordStartedAtMs: Long = 0L

    init {
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

                        logTelemetry(patchedDetection, fusion, asvResolution)
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
        _uiState.update { it.copy(useRemoteAsv = value) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateUseRemoteAsv(value)
        }
    }

    fun updateAsvEndpoint(value: String) {
        _uiState.update { it.copy(asvEndpoint = value) }
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.updateAsvEndpoint(value)
        }
    }

    fun dismissError() {
        _uiState.update { it.copy(errorMessage = null) }
    }

    private fun observeConfig() {
        viewModelScope.launch(dispatchersProvider.io) {
            securityConfigRepository.configFlow.collect { config ->
                withContext(dispatchersProvider.main) {
                    _uiState.update {
                        it.copy(
                            spoofThreshold = config.spoofThreshold,
                            asvThreshold = config.asvThreshold,
                            useRemoteAsv = config.useRemoteAsv,
                            asvEndpoint = config.asvEndpoint
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
    ): AsvResolution {
        val manualScore = state.asvScoreInput.toFloatOrNull()?.coerceIn(0f, 1f) ?: DEFAULT_ASV_SCORE
        if (!state.useRemoteAsv || state.asvEndpoint.isBlank()) {
            return AsvResolution(score = manualScore, source = "manual", latencyMs = 0L, warning = null)
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
                AsvResolution(score = result.score, source = result.source, latencyMs = result.latencyMs, warning = null)
            },
            onFailure = { throwable ->
                AsvResolution(
                    score = manualScore,
                    source = "manual-fallback",
                    latencyMs = 0L,
                    warning = "Remote ASV failed, fallback manual score: ${throwable.message}"
                )
            }
        )
    }

    private fun logTelemetry(
        detection: com.vpsaker.fake_voice_detector.domain.model.DetectionResult,
        fusion: com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult,
        asvResolution: AsvResolution
    ) {
        viewModelScope.launch(dispatchersProvider.io) {
            telemetryRepository.logAuthenticationEvent(
                AuthTelemetryEvent(
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
            )
        }
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
                dispatchersProvider = dispatchersProvider
            ) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
