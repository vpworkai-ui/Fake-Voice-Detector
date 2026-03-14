package com.vpsaker.fake_voice_detector.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.vpsaker.fake_voice_detector.core.DefaultDispatchersProvider
import com.vpsaker.fake_voice_detector.core.DispatchersProvider
import com.vpsaker.fake_voice_detector.domain.model.DetectionSession
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import com.vpsaker.fake_voice_detector.domain.repository.SecurityConfigRepository
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
                        val asvScore = current.asvScoreInput.toFloatOrNull()?.coerceIn(0f, 1f) ?: DEFAULT_ASV_SCORE
                        val fusion = fuseAuthenticationUseCase(
                            spoofProbability = patchedDetection.spoofProbability,
                            asvScore = asvScore,
                            config = SecurityConfig(
                                spoofThreshold = current.spoofThreshold,
                                asvThreshold = current.asvThreshold
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
                                sessions = (listOf(session) + it.sessions).take(MAX_SESSION_HISTORY),
                                errorMessage = null
                            )
                        }
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
                            asvThreshold = config.asvThreshold
                        )
                    }
                }
            }
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

    private companion object {
        const val DEFAULT_ASV_SCORE = 0.5f
        const val MAX_SESSION_HISTORY = 10
        val NUMBER_INPUT_REGEX = Regex("^\\d*\\.?\\d*$")
    }
}

class VoiceDetectorViewModelFactory(
    private val repository: VoiceSpoofingRepository,
    private val securityConfigRepository: SecurityConfigRepository,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModelProvider.Factory {

    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(VoiceDetectorViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return VoiceDetectorViewModel(
                repository = repository,
                securityConfigRepository = securityConfigRepository,
                analyzeVoiceSpoofingUseCase = AnalyzeVoiceSpoofingUseCase(repository),
                fuseAuthenticationUseCase = FuseAuthenticationUseCase(),
                dispatchersProvider = dispatchersProvider
            ) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
