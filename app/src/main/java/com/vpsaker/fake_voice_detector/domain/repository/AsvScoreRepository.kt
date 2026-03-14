package com.vpsaker.fake_voice_detector.domain.repository

import com.vpsaker.fake_voice_detector.domain.model.AsvScoreRequest
import com.vpsaker.fake_voice_detector.domain.model.AsvScoreResult

interface AsvScoreRepository {
    suspend fun fetchAsvScore(request: AsvScoreRequest): Result<AsvScoreResult>
}
