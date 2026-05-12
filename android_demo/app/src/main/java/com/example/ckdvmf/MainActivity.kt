package com.example.ckdvmf

import android.Manifest
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import org.json.JSONObject

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    InsuranceRiskApp()
                }
            }
        }
    }
}

class RiskViewModel : ViewModel() {
    private val _result = MutableStateFlow<RiskScoreResult?>(null)
    val result: StateFlow<RiskScoreResult?> = _result

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    private val _featureJson = MutableStateFlow<String?>(null)
    val featureJson: StateFlow<String?> = _featureJson

    private val _localFeaturePath = MutableStateFlow<String?>(null)
    val localFeaturePath: StateFlow<String?> = _localFeaturePath

    fun collectAndPredict(context: android.content.Context, serverUrl: String) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            _result.value = null
            try {
                val collector = FeatureCollector(context)
                val collectionResult = collector.collectToday()
                _featureJson.value = collectionResult.jsonText
                _localFeaturePath.value = collectionResult.savedPath

                val response = RiskApiClient(serverUrl).predict(JSONObject(collectionResult.jsonText))
                _result.value = response
            } catch (error: Exception) {
                _error.value = error.message ?: "Unknown error"
            } finally {
                _isLoading.value = false
            }
        }
    }
}

@Composable
fun InsuranceRiskApp(viewModel: RiskViewModel = viewModel()) {
    val context = LocalContext.current
    val collector = remember { FeatureCollector(context) }
    val result by viewModel.result.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val featureJson by viewModel.featureJson.collectAsState()
    val localFeaturePath by viewModel.localFeaturePath.collectAsState()

    var serverUrl by remember { mutableStateOf("http://10.0.2.2:8000") }

    val permissions = buildList {
        add(Manifest.permission.READ_CALL_LOG)
        add(Manifest.permission.READ_SMS)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            add(Manifest.permission.ACTIVITY_RECOGNITION)
        }
        add(Manifest.permission.ACCESS_COARSE_LOCATION)
        add(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.RequestMultiplePermissions()
    ) {}

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text(
            text = "MHGN Risk Demo",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0F8DE3)
        )
        Text(
            text = "실험용 Android 데이터 수집 → JSON 생성 → Python pkl 예측 → 결과 표시",
            fontSize = 13.sp,
            color = Color.Gray,
            lineHeight = 18.sp
        )

        PermissionCard(
            hasUsagePermission = collector.hasUsageStatsPermission(),
            onOpenUsageSettings = { collector.openUsageAccessSettings() },
            onRequestRuntimePermissions = {
                permissionLauncher.launch(permissions.toTypedArray())
            }
        )

        OutlinedTextField(
            value = serverUrl,
            onValueChange = { serverUrl = it },
            label = { Text("Python API URL") },
            modifier = Modifier.fillMaxWidth(),
            singleLine = true
        )
        Text(
            text = "에뮬레이터는 http://10.0.2.2:8000, 실기기는 PC와 같은 Wi-Fi에서 PC의 LAN IP를 입력",
            fontSize = 12.sp,
            color = Color.Gray,
            lineHeight = 17.sp
        )

        Button(
            onClick = { viewModel.collectAndPredict(context, serverUrl) },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            enabled = !isLoading,
            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0F8DE3)),
            shape = RoundedCornerShape(12.dp)
        ) {
            Text("데이터 수집 후 리스크 분석", color = Color.White, fontSize = 16.sp)
        }

        if (isLoading) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                CircularProgressIndicator(
                    modifier = Modifier.size(28.dp),
                    color = Color(0xFF0F8DE3)
                )
                Text("수집/예측 중...", fontSize = 14.sp)
            }
        }

        error?.let {
            InfoCard(
                title = "오류",
                body = it,
                color = Color(0xFFFFEBEE),
                titleColor = Color(0xFFE53935)
            )
        }

        localFeaturePath?.let {
            InfoCard(
                title = "생성된 Android JSON 파일",
                body = it,
                color = Color(0xFFE3F2FD),
                titleColor = Color(0xFF0F8DE3)
            )
        }

        result?.let { scores ->
            ResultSection(scores)
        }

        featureJson?.let {
            InfoCard(
                title = "전송한 Feature JSON",
                body = it,
                color = Color(0xFFF5F5F5),
                titleColor = Color.Black
            )
        }
    }
}

@Composable
fun PermissionCard(
    hasUsagePermission: Boolean,
    onOpenUsageSettings: () -> Unit,
    onRequestRuntimePermissions: () -> Unit
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("권한 설정", fontSize = 18.sp, fontWeight = FontWeight.Bold)
            Text(
                text = "UsageStats는 설정 화면에서 직접 허용해야 함. Call/SMS는 직접 설치 실험용으로 요청하며, 기기 정책에 따라 거부될 수 있음",
                fontSize = 12.sp,
                color = Color.Gray,
                lineHeight = 18.sp
            )
            Text(
                text = "Usage access: ${if (hasUsagePermission) "허용됨" else "필요"}",
                fontSize = 13.sp,
                color = if (hasUsagePermission) Color(0xFF4CAF50) else Color(0xFFE53935),
                fontWeight = FontWeight.Bold
            )
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Button(onClick = onOpenUsageSettings) {
                    Text("Usage access 열기")
                }
                Button(onClick = onRequestRuntimePermissions) {
                    Text("Call/SMS 권한 요청")
                }
            }
        }
    }
}

@Composable
fun ResultSection(result: RiskScoreResult) {
    val average = (
        result.healthRiskScore + result.mentalRiskScore + result.accidentRiskScore
    ) / 3.0

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF5CA8F0))
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text("종합 리스크 점수", fontSize = 14.sp, color = Color.White)
            Text(
                text = String.format("%.1f", average),
                fontSize = 48.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
            Text(getRiskLevel(average), fontSize = 16.sp, color = Color.White)
        }
    }

    ScoreCard("Health Risk Score", "건강 리스크", result.healthRiskScore)
    ScoreCard("Mental Risk Score", "정신 리스크", result.mentalRiskScore)
    ScoreCard("Accident Risk Score", "사고 리스크", result.accidentRiskScore)

    if (result.missingDefaultsUsed.isNotEmpty()) {
        InfoCard(
            title = "기본값 처리된 feature",
            body = result.missingDefaultsUsed.joinToString(", "),
            color = Color(0xFFFFF8E1),
            titleColor = Color(0xFFF57F17)
        )
    }
}

@Composable
fun ScoreCard(title: String, subtitle: String, score: Double) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFFF5F5F5))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(title, fontSize = 14.sp, fontWeight = FontWeight.Bold)
                    Text(subtitle, fontSize = 12.sp, color = Color.Gray)
                }
                Text(
                    text = String.format("%.1f / 100", score),
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = getScoreColor(score)
                )
            }
            LinearProgressIndicator(
                progress = { (score / 100.0).toFloat().coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
                color = getScoreColor(score),
                trackColor = Color(0xFFE0E0E0)
            )
            Text(getScoreLabel(score), fontSize = 12.sp, color = getScoreColor(score))
        }
    }
}

@Composable
fun InfoCard(title: String, body: String, color: Color, titleColor: Color) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = color)
    ) {
        Column(
            modifier = Modifier.padding(14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(title, fontSize = 14.sp, fontWeight = FontWeight.Bold, color = titleColor)
            Text(body, fontSize = 12.sp, color = Color.DarkGray, lineHeight = 17.sp)
        }
    }
}

fun getScoreColor(score: Double): Color {
    return when {
        score <= 30 -> Color(0xFF4CAF50)
        score <= 60 -> Color(0xFFFFA726)
        else -> Color(0xFFE53935)
    }
}

fun getScoreLabel(score: Double): String {
    return when {
        score <= 20 -> "매우 낮음"
        score <= 40 -> "낮음"
        score <= 60 -> "보통"
        score <= 80 -> "높음"
        else -> "매우 높음"
    }
}

fun getRiskLevel(score: Double): String {
    return when {
        score <= 20 -> "매우 안전"
        score <= 40 -> "안전"
        score <= 60 -> "보통"
        score <= 80 -> "주의"
        else -> "위험"
    }
}
