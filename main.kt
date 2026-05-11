@file:Suppress("EXPERIMENTAL_IS_NOT_ENABLED", "DEPRECATION")

package com.example.ckdvmf

import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlin.random.Random

// ===== 데이터 모델 =====
data class RiskScoreResult(
    val healthRiskScore: Int,
    val mentalRiskScore: Int,
    val accidentRiskScore: Int
)

// ===== ViewModel =====
class RiskViewModel : ViewModel() {
    private val tag = "RiskViewModel"

    private val _result = MutableStateFlow<RiskScoreResult?>(null)
    val result: StateFlow<RiskScoreResult?> = _result

    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading

    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error

    fun fetchRiskScores() {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            _result.value = null

            try {
                Log.d(tag, "리스크 점수 요청 시작")

                // 백엔드 미구현: 랜덤 숫자 생성 (1-100)
                // 실제 백엔드 연동 시 이 부분을 API 호출로 교체
                delay(3000) // 서버 응답 시뮬레이션

                val scores = RiskScoreResult(
                    healthRiskScore = Random.nextInt(1, 101),
                    mentalRiskScore = Random.nextInt(1, 101),
                    accidentRiskScore = Random.nextInt(1, 101)
                )

                Log.d(tag, "점수 수신: health=${scores.healthRiskScore}, mental=${scores.mentalRiskScore}, accident=${scores.accidentRiskScore}")

                _result.value = scores
                _isLoading.value = false

            } catch (e: Exception) {
                Log.e(tag, "Exception: ${e.message}", e)
                _error.value = "데이터 로드 실패: ${e.message}"
                _isLoading.value = false
            }
        }
    }

    fun retry() {
        _result.value = null
        _error.value = null
        fetchRiskScores()
    }
}

// ===== MainActivity =====
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            InsuranceRiskApp()
        }
    }
}

// ===== 앱 =====
@Composable
fun InsuranceRiskApp() {
    val navController = rememberNavController()
    val viewModel: RiskViewModel = viewModel()

    NavHost(navController = navController, startDestination = "loading") {
        composable("loading") { LoadingScreen(navController, viewModel) }
        composable("analysis") { AnalysisScreen(navController, viewModel) }
    }
}

// ===== 로딩 스크린 =====
@Composable
fun LoadingScreen(navController: NavController, viewModel: RiskViewModel) {
    val result by viewModel.result.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()

    // 앱 실행 시 자동으로 데이터 요청
    LaunchedEffect(Unit) {
        viewModel.fetchRiskScores()
    }

    // 결과 도착 시 분석 화면으로 이동
    if (result != null && !isLoading) {
        LaunchedEffect(Unit) {
            delay(300)
            navController.navigate("analysis") {
                popUpTo("loading") { inclusive = true }
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // 로고 텍스트
        Text(
            text = "Insurance Risk",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = Color(0xFF0F8DE3)
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "리스크 분석 서비스",
            fontSize = 14.sp,
            color = Color.Gray
        )

        Spacer(modifier = Modifier.height(40.dp))

        // 로딩 인디케이터
        CircularProgressIndicator(
            modifier = Modifier.size(60.dp),
            color = Color(0xFF0F8DE3),
            strokeWidth = 4.dp
        )

        Spacer(modifier = Modifier.height(24.dp))

        Text(
            text = "데이터를 불러오는 중입니다...",
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
            color = Color.Black
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "잠시만 기다려 주세요",
            fontSize = 13.sp,
            color = Color.Gray
        )

        // 에러 발생 시
        error?.let { errorMessage ->
            Spacer(modifier = Modifier.height(24.dp))

            Text(
                text = errorMessage,
                fontSize = 13.sp,
                color = Color.Red
            )

            Spacer(modifier = Modifier.height(12.dp))

            Button(
                onClick = { viewModel.retry() },
                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0F8DE3)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Text("다시 시도", color = Color.White)
            }
        }
    }
}

// ===== 분석 스크린 =====
@Composable
fun AnalysisScreen(navController: NavController, viewModel: RiskViewModel) {
    val result by viewModel.result.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.White)
            .verticalScroll(rememberScrollState())
    ) {
        // 상단 헤더
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(Color(0xFF0F8DE3))
                .padding(20.dp)
        ) {
            Column {
                Text(
                    text = "리스크 분석 결과",
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.White
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "보험료 산정을 위한 개인 리스크 분석",
                    fontSize = 13.sp,
                    color = Color.White.copy(alpha = 0.8f)
                )
            }
        }

        result?.let { scores ->
            val averageScore = (scores.healthRiskScore + scores.mentalRiskScore + scores.accidentRiskScore) / 3

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                // 종합 점수 카드
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFF5CA8F0)
                    )
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "종합 리스크 점수",
                            fontSize = 14.sp,
                            color = Color.White.copy(alpha = 0.9f)
                        )
                        Text(
                            text = "$averageScore",
                            fontSize = 48.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Text(
                            text = getRiskLevel(averageScore),
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                        Spacer(modifier = Modifier.height(4.dp))
                        Text(
                            text = getInsuranceMessage(averageScore),
                            fontSize = 13.sp,
                            color = Color.White.copy(alpha = 0.85f)
                        )
                    }
                }

                // 개별 점수 카드들
                RiskScoreCard(
                    title = "Health Risk Score",
                    subtitle = "건강 리스크",
                    score = scores.healthRiskScore,
                    description = getHealthDescription(scores.healthRiskScore)
                )

                RiskScoreCard(
                    title = "Mental Risk Score",
                    subtitle = "정신 리스크",
                    score = scores.mentalRiskScore,
                    description = getMentalDescription(scores.mentalRiskScore)
                )

                RiskScoreCard(
                    title = "Accident Risk Score",
                    subtitle = "사고 리스크",
                    score = scores.accidentRiskScore,
                    description = getAccidentDescription(scores.accidentRiskScore)
                )

                // 보험료 안내 카드
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFFF5F5F5)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Text(
                            text = "보험료 산정 안내",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )

                        InsuranceInfoRow("건강 리스크", scores.healthRiskScore)
                        InsuranceInfoRow("정신 리스크", scores.mentalRiskScore)
                        InsuranceInfoRow("사고 리스크", scores.accidentRiskScore)

                        Divider(color = Color(0xFFE0E0E0), thickness = 1.dp)

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "종합 보험료 조정",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                            Text(
                                text = getInsurancePremiumText(averageScore),
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = getInsurancePremiumColor(averageScore)
                            )
                        }
                    }
                }

                // 주의 안내 카드
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(12.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = Color(0xFFFFF8E1)
                    )
                ) {
                    Column(
                        modifier = Modifier.padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Text(
                            text = "⚠ 안내사항",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFF57F17)
                        )
                        Text(
                            text = "본 분석 결과는 참고용이며, 실제 보험료 산정은 보험사의 심사 기준에 따라 달라질 수 있습니다.",
                            fontSize = 12.sp,
                            color = Color(0xFF795548),
                            lineHeight = 18.sp
                        )
                        Text(
                            text = "리스크 점수가 높을수록 위험도가 높음을 의미합니다. (1: 매우 낮음, 100: 매우 높음)",
                            fontSize = 12.sp,
                            color = Color(0xFF795548),
                            lineHeight = 18.sp
                        )
                    }
                }

                // 다시 분석 버튼
                Button(
                    onClick = {
                        viewModel.retry()
                        navController.navigate("loading") {
                            popUpTo("analysis") { inclusive = true }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0F8DE3)),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text("다시 분석하기", fontSize = 16.sp, color = Color.White)
                }

                Spacer(modifier = Modifier.height(16.dp))
            }
        }
    }
}

// ===== 개별 리스크 점수 카드 =====
@Composable
fun RiskScoreCard(title: String, subtitle: String, score: Int, description: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
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
                    Text(
                        text = title,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )
                    Text(
                        text = subtitle,
                        fontSize = 12.sp,
                        color = Color.Gray
                    )
                }
                Text(
                    text = "$score / 100",
                    fontSize = 24.sp,
                    fontWeight = FontWeight.Bold,
                    color = getScoreColor(score)
                )
            }

            // 점수 바
            LinearProgressIndicator(
                progress = { score / 100f },
                modifier = Modifier
                    .fillMaxWidth()
                    .height(8.dp),
                color = getScoreColor(score),
                trackColor = Color(0xFFE0E0E0),
            )

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = getScoreLabel(score),
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    color = getScoreColor(score)
                )
            }

            Text(
                text = description,
                fontSize = 12.sp,
                color = Color.Gray,
                lineHeight = 18.sp
            )
        }
    }
}

// ===== 보험료 안내 행 =====
@Composable
fun InsuranceInfoRow(label: String, score: Int) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontSize = 13.sp,
            color = Color.Gray
        )
        Row(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = "$score 점",
                fontSize = 13.sp,
                color = Color.Black
            )
            Text(
                text = getInsurancePremiumText(score),
                fontSize = 13.sp,
                fontWeight = FontWeight.Bold,
                color = getInsurancePremiumColor(score)
            )
        }
    }
}

// ===== 유틸리티 함수들 =====

fun getScoreColor(score: Int): Color {
    return when {
        score <= 30 -> Color(0xFF4CAF50)   // 녹색: 낮은 리스크
        score <= 60 -> Color(0xFFFFA726)   // 주황: 중간 리스크
        else -> Color(0xFFE53935)          // 빨강: 높은 리스크
    }
}

fun getScoreLabel(score: Int): String {
    return when {
        score <= 20 -> "매우 낮음"
        score <= 40 -> "낮음"
        score <= 60 -> "보통"
        score <= 80 -> "높음"
        else -> "매우 높음"
    }
}

fun getRiskLevel(averageScore: Int): String {
    return when {
        averageScore <= 20 -> "🟢 매우 안전"
        averageScore <= 40 -> "🟢 안전"
        averageScore <= 60 -> "🟡 보통"
        averageScore <= 80 -> "🟠 주의"
        else -> "🔴 위험"
    }
}

fun getInsuranceMessage(averageScore: Int): String {
    return when {
        averageScore <= 30 -> "보험료 할인 대상입니다"
        averageScore <= 60 -> "표준 보험료가 적용됩니다"
        else -> "보험료 할증이 적용될 수 있습니다"
    }
}

fun getInsurancePremiumText(score: Int): String {
    return when {
        score <= 25 -> "할인 15%"
        score <= 40 -> "할인 5%"
        score <= 60 -> "표준"
        score <= 80 -> "할증 10%"
        else -> "할증 20%"
    }
}

fun getInsurancePremiumColor(score: Int): Color {
    return when {
        score <= 40 -> Color(0xFF4CAF50)   // 할인: 녹색
        score <= 60 -> Color(0xFF757575)   // 표준: 회색
        else -> Color(0xFFE53935)          // 할증: 빨강
    }
}

fun getHealthDescription(score: Int): String {
    return when {
        score <= 30 -> "건강 상태가 양호합니다. 규칙적인 생활 습관이 잘 유지되고 있으며, 주요 건강 지표가 정상 범위에 있습니다."
        score <= 60 -> "건강 상태가 보통입니다. 일부 건강 지표에서 주의가 필요하며, 정기적인 건강 검진을 권장합니다."
        else -> "건강 리스크가 높습니다. 의료 전문가와의 상담을 통해 건강 관리 계획을 수립하는 것을 권장합니다."
    }
}

fun getMentalDescription(score: Int): String {
    return when {
        score <= 30 -> "정신 건강 상태가 안정적입니다. 스트레스 관리가 잘 되고 있으며, 전반적인 심리 상태가 양호합니다."
        score <= 60 -> "정신 건강에 일부 주의가 필요합니다. 적절한 휴식과 스트레스 관리 활동을 권장합니다."
        else -> "정신 건강 리스크가 높습니다. 전문 상담사와의 상담을 통해 심리적 안정을 도모하는 것을 권장합니다."
    }
}

fun getAccidentDescription(score: Int): String {
    return when {
        score <= 30 -> "사고 발생 리스크가 낮습니다. 안전한 생활 환경과 습관이 잘 유지되고 있습니다."
        score <= 60 -> "사고 리스크가 보통 수준입니다. 일상에서의 안전 수칙 준수에 조금 더 신경을 기울이는 것을 권장합니다."
        else -> "사고 리스크가 높습니다. 생활 환경 및 활동에서의 안전 관리를 강화하는 것을 권장합니다."
    }
}
