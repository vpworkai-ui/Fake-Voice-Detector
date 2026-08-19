package com.vpsaker.fake_voice_detector.domain.usecase

import com.vpsaker.fake_voice_detector.domain.model.AuthenticationDecision
import com.vpsaker.fake_voice_detector.domain.model.FusionDecisionResult

class EvaluateSpoofResultUseCase {

    operator fun invoke(spoofProbability: Float, spoofThreshold: Float): FusionDecisionResult {
        val threshold = spoofThreshold.coerceIn(0.05f, 0.95f)
        val reviewBand = 0.08f
        val allowBand = (threshold - reviewBand).coerceAtLeast(0f)
        val decision = when {
            spoofProbability >= threshold -> AuthenticationDecision.BLOCK
            spoofProbability >= allowBand -> AuthenticationDecision.REVIEW
            else -> AuthenticationDecision.ALLOW
        }
        val reason = when (decision) {
            AuthenticationDecision.ALLOW -> "Spoof risk low and safely below threshold"
            AuthenticationDecision.REVIEW -> "Spoof risk near threshold, should be reviewed"
            AuthenticationDecision.BLOCK -> "Spoof risk exceeded threshold"
        }

        return FusionDecisionResult(
            decision = decision,
            reason = reason,
            spoofProbability = spoofProbability,
            spoofThreshold = threshold,
            confidence = kotlin.math.abs(spoofProbability - threshold)
                .div(threshold.coerceAtLeast(0.05f))
                .coerceIn(0f, 1f),
            meetsSpoofThreshold = spoofProbability < threshold
        )
    }
}
