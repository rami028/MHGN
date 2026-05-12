package com.example.ckdvmf

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class RiskApiClient(private val baseUrl: String) {
    private val client = OkHttpClient()
    private val jsonMediaType = "application/json; charset=utf-8".toMediaType()

    suspend fun predict(featuresJson: JSONObject): RiskScoreResult = withContext(Dispatchers.IO) {
        val url = baseUrl.trimEnd('/') + "/predict-risk"
        val body = featuresJson.toString().toRequestBody(jsonMediaType)
        val request = Request.Builder()
            .url(url)
            .post(body)
            .build()

        client.newCall(request).execute().use { response ->
            val responseText = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                error("API ${response.code}: $responseText")
            }

            val root = JSONObject(responseText)
            val scores = root.getJSONObject("risk_scores")
            val missingArray = root.optJSONArray("missing_defaults_used")
            val missing = mutableListOf<String>()
            if (missingArray != null) {
                for (i in 0 until missingArray.length()) {
                    missing.add(missingArray.getString(i))
                }
            }

            RiskScoreResult(
                healthRiskScore = scores.getDouble("health_risk_score"),
                mentalRiskScore = scores.getDouble("mental_risk_score"),
                accidentRiskScore = scores.getDouble("accident_risk_score"),
                savedFeaturePath = root.optString("feature_json_saved_to"),
                missingDefaultsUsed = missing
            )
        }
    }
}
