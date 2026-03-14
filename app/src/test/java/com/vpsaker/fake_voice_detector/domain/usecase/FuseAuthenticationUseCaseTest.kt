package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig
import org.junit.Assert.assertEquals
import org.junit.Test

class FuseAuthenticationUseCaseTest {

    private val useCase = FuseAuthenticationUseCase()

    @Test
    fun `block when spoof probability is above threshold`() {
        val result = useCase(
            spoofProbability = 0.82f,
            asvScore = 0.91f,
            config = SecurityConfig(spoofThreshold = 0.5f, asvThreshold = 0.75f)
        )

        assertEquals(AuthenticationDecision.BLOCK, result.decision)
    }

    @Test
    fun `allow when spoof risk is low and asv is high`() {
        val result = useCase(
            spoofProbability = 0.12f,
            asvScore = 0.86f,
            config = SecurityConfig(spoofThreshold = 0.5f, asvThreshold = 0.75f)
        )

        assertEquals(AuthenticationDecision.ALLOW, result.decision)
    }

    @Test
    fun `review when asv is borderline and spoof risk very low`() {
        val result = useCase(
            spoofProbability = 0.10f,
            asvScore = 0.69f,
            config = SecurityConfig(spoofThreshold = 0.5f, asvThreshold = 0.75f)
        )

        assertEquals(AuthenticationDecision.REVIEW, result.decision)
    }
}
