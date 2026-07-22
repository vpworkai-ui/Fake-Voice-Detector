package com.vpsaker.fake_voice_detector.data.detection

interface SpoofDetectorEngine {
    val modelName: String

    /**
     * Detect spoof probability from raw PCM audio.
     * The engine is responsible for computing all required features/spectrograms internally.
     * @param pcm     Raw 16-bit PCM samples (already normalised by recorder)
     * @param sampleRateHz Sample rate (typically 16000)
     * @return Probability ∈ [0,1] where 1.0 = definitely spoof
     */
    fun detectSpoofProbability(pcm: ShortArray, sampleRateHz: Int): Float
}
