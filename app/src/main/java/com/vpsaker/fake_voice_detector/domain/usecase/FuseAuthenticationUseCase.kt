package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult
import com.vpsaker.fake_voice_detector.domain.model.SecurityConfig

class FuseAuthenticationUseCase {

    operator fun invoke(
        spoofProbability: Float,
        asvScore: Float,
        config: SecurityConfig
    ): FusionDecisionResult {
        val meetsSpoofThreshold = spoofProbability < config.spoofThreshold
        val meetsAsvThreshold = asvScore >= config.asvThreshold

        if (!meetsSpoofThreshold) {
            return FusionDecisionResult(
                decision = AuthenticationDecision.BLOCK,
                reason = "High spoof risk",
                asvScore = asvScore,
                spoofProbability = spoofProbability,
                meetsAsvThreshold = meetsAsvThreshold,
                meetsSpoofThreshold = false
            )
        }

        if (meetsAsvThreshold) {
            return FusionDecisionResult(
                decision = AuthenticationDecision.ALLOW,
                reason = "ASV accepted and spoof risk low",
                asvScore = asvScore,
                spoofProbability = spoofProbability,
                meetsAsvThreshold = true,
                meetsSpoofThreshold = true
            )
        }

        val borderlineAsv = asvScore >= (config.asvThreshold - 0.08f).coerceAtLeast(0f)
        val veryLowSpoofRisk = spoofProbability <= (config.spoofThreshold * 0.55f)
        if (borderlineAsv && veryLowSpoofRisk) {
            return FusionDecisionResult(
                decision = AuthenticationDecision.REVIEW,
                reason = "Borderline ASV, require step-up verification",
                asvScore = asvScore,
                spoofProbability = spoofProbability,
                meetsAsvThreshold = false,
                meetsSpoofThreshold = true
            )
        }

        return FusionDecisionResult(
            decision = AuthenticationDecision.BLOCK,
            reason = "ASV score below threshold",
            asvScore = asvScore,
            spoofProbability = spoofProbability,
            meetsAsvThreshold = false,
            meetsSpoofThreshold = true
        )
    }
}
