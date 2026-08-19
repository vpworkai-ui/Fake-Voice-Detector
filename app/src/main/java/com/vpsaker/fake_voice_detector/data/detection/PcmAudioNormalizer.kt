package com.vpsaker.fake_voice_detector.data.detection

import kotlin.math.min

class PcmAudioNormalizer {

    fun normalize(audioPcm: ShortArray, targetSampleCount: Int? = null): FloatArray {
        val outputSize = targetSampleCount ?: audioPcm.size
        if (outputSize <= 0) return FloatArray(0)

        val signal = FloatArray(outputSize)
        val copyCount = min(audioPcm.size, outputSize)
        for (index in 0 until copyCount) {
            signal[index] = audioPcm[index] / Short.MAX_VALUE.toFloat()
        }
        return signal
    }
}
