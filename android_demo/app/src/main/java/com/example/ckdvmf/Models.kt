package com.example.ckdvmf

data class RiskScoreResult(
    val healthRiskScore: Double,
    val mentalRiskScore: Double,
    val accidentRiskScore: Double,
    val savedFeaturePath: String,
    val missingDefaultsUsed: List<String>
)

data class CollectionResult(
    val jsonText: String,
    val savedPath: String
)
