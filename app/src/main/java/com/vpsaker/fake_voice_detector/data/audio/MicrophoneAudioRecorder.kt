package com.vpsaker.fake_voice_detector.data.audio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder

class MicrophoneAudioRecorder : AudioRecorder {

    @Volatile
    private var isRecording = false

    private val capturedSamples: MutableList<Short> = ArrayList()
    private var audioRecord: AudioRecord? = null
    private var readerThread: Thread? = null

    override fun start(sampleRateHz: Int): Result<Unit> {
        if (isRecording) return Result.success(Unit)

        return try {
            val minBufferSize = AudioRecord.getMinBufferSize(
                sampleRateHz,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT
            )
            if (minBufferSize <= 0) {
                return Result.failure(IllegalStateException("Unable to resolve buffer size"))
            }

            val recorder = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                sampleRateHz,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                minBufferSize * BUFFER_MULTIPLIER
            )

            if (recorder.state != AudioRecord.STATE_INITIALIZED) {
                recorder.release()
                return Result.failure(IllegalStateException("AudioRecord initialization failed"))
            }

            synchronized(capturedSamples) {
                capturedSamples.clear()
            }
            recorder.startRecording()
            audioRecord = recorder
            isRecording = true

            readerThread = Thread {
                val localBuffer = ShortArray(READ_CHUNK_SIZE)
                while (isRecording) {
                    val read = recorder.read(localBuffer, 0, localBuffer.size)
                    if (read > 0) {
                        synchronized(capturedSamples) {
                            for (i in 0 until read) {
                                capturedSamples.add(localBuffer[i])
                            }
                        }
                    }
                }
            }.apply {
                name = "mic-recorder-thread"
                start()
            }

            Result.success(Unit)
        } catch (securityException: SecurityException) {
            Result.failure(securityException)
        } catch (throwable: Throwable) {
            Result.failure(throwable)
        }
    }

    override fun stop(): ShortArray {
        if (!isRecording) return ShortArray(0)

        isRecording = false
        readerThread?.join(STOP_TIMEOUT_MS)
        readerThread = null

        audioRecord?.runCatching {
            stop()
            release()
        }
        audioRecord = null

        return synchronized(capturedSamples) {
            capturedSamples.toShortArray().also { capturedSamples.clear() }
        }
    }

    override fun isRecording(): Boolean = isRecording

    companion object {
        private const val READ_CHUNK_SIZE = 2048
        private const val BUFFER_MULTIPLIER = 2
        private const val STOP_TIMEOUT_MS = 500L
    }
}
