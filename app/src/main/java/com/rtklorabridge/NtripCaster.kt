package com.rtklorabridge

import kotlinx.coroutines.*
import kotlinx.coroutines.flow.MutableStateFlow
import java.io.OutputStream
import java.net.ServerSocket
import java.net.Socket
import java.util.concurrent.CopyOnWriteArrayList

class NtripCaster(private val port: Int = 2101) {

    private val clients = CopyOnWriteArrayList<OutputStream>()
    private var serverJob: Job? = null

    val clientCount = MutableStateFlow(0)

    fun start(scope: CoroutineScope) {
        serverJob = scope.launch(Dispatchers.IO) {
            val server = ServerSocket(port)
            while (isActive) {
                try {
                    val socket = server.accept()
                    launch { handleClient(socket) }
                } catch (e: Exception) {
                    if (!isActive) break
                }
            }
        }
    }

    private fun handleClient(socket: Socket) {
        try {
            // NTRIP v1 핸드셰이크
            val reader = socket.getInputStream().bufferedReader()
            val request = reader.readLine() ?: return
            // "GET /RTCM32 HTTP/1.0" 형태

            val response = buildString {
                append("ICY 200 OK\r\n")
                append("Content-Type: gnss/data\r\n")
                append("Cache-Control: no-cache\r\n")
                append("\r\n")
            }
            val out = socket.getOutputStream()
            out.write(response.toByteArray())
            out.flush()

            clients.add(out)
            clientCount.value = clients.size
        } catch (e: Exception) {
            // 연결 실패
        }
    }

    fun broadcast(data: ByteArray) {
        val dead = mutableListOf<OutputStream>()
        clients.forEach { stream ->
            try {
                stream.write(data)
                stream.flush()
            } catch (e: Exception) {
                dead.add(stream)
            }
        }
        if (dead.isNotEmpty()) {
            clients.removeAll(dead)
            clientCount.value = clients.size
        }
    }

    fun stop() {
        serverJob?.cancel()
        clients.clear()
        clientCount.value = 0
    }
}
