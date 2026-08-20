package com.rtklorabridge

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.core.content.ContextCompat
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

class MainActivity : ComponentActivity() {

    private val viewModel: RtkViewModel by viewModels()

    private val notificationPermissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) {
            // 권한 허용 여부와 관계없이 서비스 시작 시도
            viewModel.startService()
        }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            RtkBridgeScreen(viewModel)
        }

        // 앱 시작 시 알림 권한 요청 후 서비스 자동 실행
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.POST_NOTIFICATIONS
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                viewModel.startService()
            } else {
                notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        } else {
            viewModel.startService()
        }
    }
}

@Composable
fun RtkBridgeScreen(viewModel: RtkViewModel) {
    val isConnected by viewModel.isConnected.collectAsState()
    val bytesPerSec by viewModel.bytesPerSec.collectAsState()
    val clientCount by viewModel.clientCount.collectAsState()
    val serviceRunning by viewModel.serviceRunning.collectAsState()
    val stationId by viewModel.stationId.collectAsState()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0F1923))
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.SpaceEvenly
    ) {

        // 제목
        Text(
            text = "RTK LoRa Bridge",
            color = Color.White,
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold
        )

        // 연결 상태 원형 표시
        Box(
            modifier = Modifier
                .size(140.dp)
                .background(
                    color = when {
                        !serviceRunning -> Color(0xFF374151)
                        isConnected -> Color(0xFF22c55e)
                        else -> Color(0xFFef4444)
                    },
                    shape = CircleShape
                ),
            contentAlignment = Alignment.Center
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    text = when {
                        !serviceRunning -> "정지"
                        isConnected -> "수신중"
                        else -> "대기중"
                    },
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.Bold
                )
                if (isConnected && bytesPerSec > 0) {
                    Text(
                        text = "${bytesPerSec}B/s",
                        color = Color.White.copy(alpha = 0.8f),
                        fontSize = 12.sp
                    )
                }
            }
        }

        // 상태 카드
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1e2a3a))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                StatusRow("NTRIP 서버", "127.0.0.1:2101")
                Divider(color = Color(0xFF374151), modifier = Modifier.padding(vertical = 8.dp))
                StatusRow("LoRa 수신기", if (isConnected) "연결됨 ✅" else "연결 안됨 ❌")
                Divider(color = Color(0xFF374151), modifier = Modifier.padding(vertical = 8.dp))
                StatusRow("기준국 ID", stationId?.toString() ?: "-")
                Divider(color = Color(0xFF374151), modifier = Modifier.padding(vertical = 8.dp))
                StatusRow("수신 속도", "${bytesPerSec} bytes/s")
                Divider(color = Color(0xFF374151), modifier = Modifier.padding(vertical = 8.dp))
                StatusRow("접속 클라이언트", "${clientCount}대")
            }
        }

        // CHCNav 설정 안내 카드
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(12.dp),
            colors = CardDefaults.cardColors(containerColor = Color(0xFF1e3a5f))
        ) {
            Column(modifier = Modifier.padding(16.dp)) {
                Text(
                    text = "CHCNav / FJDynamics 설정",
                    color = Color(0xFF93c5fd),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold
                )
                Spacer(Modifier.height(8.dp))
                Text("서버:  127.0.0.1", color = Color.White, fontSize = 14.sp)
                Text("포트:  2101", color = Color.White, fontSize = 14.sp)
                Text("ID/PW: 비워두기", color = Color.White, fontSize = 14.sp)
            }
        }

        // 서비스 시작/정지 버튼
        Button(
            onClick = {
                if (serviceRunning) viewModel.stopService()
                else viewModel.startService()
            },
            modifier = Modifier
                .fillMaxWidth()
                .height(56.dp),
            shape = RoundedCornerShape(12.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = if (serviceRunning) Color(0xFFef4444) else Color(0xFF22c55e)
            )
        ) {
            Text(
                text = if (serviceRunning) "서비스 정지" else "서비스 시작",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
fun StatusRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label, color = Color(0xFF9ca3af), fontSize = 14.sp)
        Text(value, color = Color.White, fontSize = 14.sp, fontWeight = FontWeight.Bold)
    }
}
