<template>
  <div>
    <div class="nav">
      <h1>🔬 质量检验知识库</h1>
      <div class="nav-links">
        <router-link to="/chat">💬 对话</router-link>
        <router-link to="/upload">📤 上传</router-link>
        <router-link to="/knowledge">📚 知识库</router-link>
        <router-link to="/monitor">📊 监控</router-link>
      </div>
    </div>

    <div class="container">
      <div class="session-info">
        <label>Session ID:</label>
        <input v-model="sessionId" placeholder="输入 Session ID">
        <button class="btn-secondary" @click="showHistory">📋 历史记录</button>
        <button class="btn-danger" @click="clearChat">🗑️ 清空对话</button>
      </div>

      <div class="chat-box" ref="chatBox">
        <div v-for="(msg, i) in messages" :key="i" class="message" :class="msg.role">
          <div class="message-content" v-html="msg.content"></div>
        </div>
        <div v-if="isLoading" class="message assistant">
          <div class="message-content">
            <div class="loading">
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
              <div class="loading-dot"></div>
              {{ thinkingLabel }}
            </div>
          </div>
        </div>
      </div>

      <div class="input-box">
        <input v-model="question" placeholder="输入你的问题..." @keypress.enter="sendMessage" :disabled="isLoading">
        <button v-if="isLoading" class="btn-danger" @click="stopMessage">⏸ 停止</button>
        <button v-else-if="lastCanceled" class="btn-secondary" @click="resumeLast">▶ 继续上次</button>
        <button v-if="!isLoading" @click="sendMessage">发送</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import { useChatStore } from '../store/chat'
import { storeToRefs } from 'pinia'

const chatStore = useChatStore()
const { messages, isLoading, lastCanceled, thinkingLabel } = storeToRefs(chatStore)

const question = ref('')
const sessionId = ref('user-001')
const chatBox = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight
  })
}

watch(messages, scrollToBottom, { deep: true })

async function sendMessage() {
  if (!question.value.trim() || isLoading.value) return
  const q = question.value
  question.value = ''
  await chatStore.sendMessage(q)
}

async function stopMessage() {
  await chatStore.cancelCurrent()
}

async function resumeLast() {
  await chatStore.resumeLast()
}

function clearChat() {
  chatStore.clearChat()
}

async function showHistory() {
  try {
    const response = await fetch(`/api/v1/agent/history/${sessionId.value}?limit=20`)
    const data = await response.json()
    if (data.history && data.history.length > 0) {
      let html = '<div style="padding:20px">'
      html += '<h3>📋 对话历史</h3>'
      data.history.forEach(msg => {
        const role = msg.role === 'user' ? '👤' : '🤖'
        html += `<div style="margin:10px 0;padding:10px;background:#f8f8f8;border-radius:6px">
          <strong>${role}</strong><br>${msg.content}</div>`
      })
      html += '</div>'
      const win = window.open('', '_blank', 'width=600,height=500')
      win.document.write(html)
    } else {
      alert('暂无历史记录')
    }
  } catch (e) {
    alert('获取历史失败')
  }
}
</script>