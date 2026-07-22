package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import org.junit.Assert.assertEquals
import org.junit.Test

class EvaluateSpoofResultUseCaseTest {

    private val useCase = EvaluateSpoofResultUseCase()

    @Test
    fun `block when spoof probability is above threshold`() {
        val result = useCase(
            spoofProbability = 0.82f,
            spoofThreshold = 0.5f
        )

        assertEquals(AuthenticationDecision.BLOCK, result.decision)
    }

    @Test
    fun `allow when spoof risk is safely below threshold`() {
        val result = useCase(
            spoofProbability = 0.12f,
            spoofThreshold = 0.5f
        )

        assertEquals(AuthenticationDecision.ALLOW, result.decision)
    }

    @Test
    fun `review when spoof risk is near threshold`() {
        val result = useCase(
            spoofProbability = 0.45f,
            spoofThreshold = 0.5f
        )

        assertEquals(AuthenticationDecision.REVIEW, result.decision)
    }
}
