package com.vpsaker.fake_voice_detector.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.vpsaker.fake_voice_detector.core.DispatchersProvider
import com.vpsaker.fake_voice_detector.core.DefaultDispatchersProvider
import com.vpsaker.fake_voice_detector.domain.repository.VoiceSpoofingRepository
import com.vpsaker.fake_voice_detector.domain.usecase.AnalyzeVoiceSpoofingUseCase
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
    private val analyzeVoiceSpoofingUseCase: AnalyzeVoiceSpoofingUseCase,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModel() {

    private val _uiState = MutableStateFlow(DetectorUiState())
    val uiState: StateFlow<DetectorUiState> = _uiState.asStateFlow()

    private var recordTickerJob: Job? = null
    private var recordStartedAtMs: Long = 0L

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
                        _uiState.update {
                            it.copy(
                                isAnalyzing = false,
                                result = detection,
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

    fun dismissError() {
        _uiState.update { it.copy(errorMessage = null) }
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
}

class VoiceDetectorViewModelFactory(
    private val repository: VoiceSpoofingRepository,
    private val dispatchersProvider: DispatchersProvider = DefaultDispatchersProvider
) : ViewModelProvider.Factory {

    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        if (modelClass.isAssignableFrom(VoiceDetectorViewModel::class.java)) {
            @Suppress("UNCHECKED_CAST")
            return VoiceDetectorViewModel(
                repository = repository,
                analyzeVoiceSpoofingUseCase = AnalyzeVoiceSpoofingUseCase(repository),
                dispatchersProvider = dispatchersProvider
            ) as T
        }
        throw IllegalArgumentException("Unknown ViewModel class: ${modelClass.name}")
    }
}
