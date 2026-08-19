package com.vpsaker.fake_voice_detector.data.audio

class PcmSignalNormalizer {

    fun normalize(pcm: ShortArray): FloatArray {
        return FloatArray(pcm.size) { index -> pcm[index] / Short.MAX_VALUE.toFloat() }
    }
}
