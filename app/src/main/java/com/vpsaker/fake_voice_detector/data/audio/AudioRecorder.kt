package com.vpsaker.fake_voice_detector.data.audio

interface AudioRecorder {
    fun start(sampleRateHz: Int): Result<Unit>
    fun stop(): ShortArray
    fun isRecording(): Boolean
}
