<template>
  <div>
    <NavBar />

    <div class="container">

      <!-- 已收录客户 -->
      <div v-if="customers.length" class="card" style="margin-bottom:16px;padding:16px 20px">
        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
          <span style="font-size:13px;color:#6b7280;white-space:nowrap">已收录客户 SIP：</span>
          <span
            v-for="c in customers" :key="c.customer"
            @click="toggleCustomer(c.customer)"
            :title="`${c.doc_count} 份文件 / ${c.part_count} 种零件`"
            style="display:inline-flex;align-items:center;gap:4px;padding:4px 12px;
                   border-radius:999px;font-size:13px;cursor:pointer;
                   border:1px solid;transition:all 0.15s"
            :style="activeCustomer === c.customer
              ? 'background:#4f46e5;color:white;border-color:#4f46e5'
              : 'background:#eef2ff;color:#4f46e5;border-color:#c7d2fe'"
          >
            {{ c.customer }}
            <span style="font-size:11px;opacity:0.75">{{ c.doc_count }}份</span>
          </span>
        </div>

        <!-- 零件面板 -->
        <div v-if="activeCustomer && customerParts !== null"
          style="margin-top:14px;border-top:1px solid #e5e7eb;padding-top:14px">
          <div v-if="partsLoading" style="color:#9ca3af;font-size:13px">加载中...</div>
          <div v-else-if="!customerParts.length" style="color:#9ca3af;font-size:13px">暂无零件数据</div>
          <div v-else>
            <div style="font-size:12px;color:#6b7280;margin-bottom:10px">
              {{ activeCustomer }} · 共 {{ customerParts.length }} 条 SIP 记录
            </div>
            <div style="display:flex;flex-wrap:wrap;gap:8px">
              <div
                v-for="p in customerParts" :key="p.document_id + p.part_name"
                style="padding:8px 12px;background:#f9fafb;border:1px solid #e5e7eb;
                       border-radius:8px;font-size:13px;min-width:180px"
              >
                <div style="font-weight:500;color:#111827;margin-bottom:2px">{{ p.part_name }}</div>
                <div style="font-size:11px;color:#6b7280;margin-bottom:6px">
                  {{ p.document_id }} · v{{ p.version }}
                </div>
                <a v-if="p.pdf_exists"
                  :href="`/${p.pdf_url}`" target="_blank"
                  style="font-size:12px;color:#4f46e5;text-decoration:none;
                         display:inline-flex;align-items:center;gap:3px"
                >📄 查看 SIP</a>
                <span v-else style="font-size:12px;color:#d1d5db">暂无 PDF</span>
                <button
                  v-if="auth.isAdmin"
                  @click="deleteSip(p.document_id, p.part_name)"
                  style="display:block;margin-top:6px;padding:3px 10px;background:#fee2e2;
                         color:#dc2626;border:1px solid #fca5a5;border-radius:4px;
                         font-size:11px;cursor:pointer"
                >删除</button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="session-info">
        <label>Session ID:</label>
        <input v-model="sessionId" placeholder="输入 Session ID">
        <button class="btn-secondary" @click="showHistory">📋 历史记录</button>
        <button class="btn-danger" @click="clearChat">🗑️ 清空对话</button>
      </div>

      <div class="chat-box" ref="chatBox">
        <!-- 欢迎页：无消息时显示提示词 -->
        <div v-if="!messages.length" style="padding:32px 16px;text-align:center">
          <p style="color:#9ca3af;font-size:14px;margin-bottom:20px">你可以这样提问：</p>
          <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;max-width:720px;margin:0 auto">
            <button
              v-for="tip in promptTips" :key="tip.text"
              @click="sendTip(tip.text)"
              :title="tip.text"
              style="padding:6px 14px;background:#f9fafb;border:1px solid #e5e7eb;
                     border-radius:8px;font-size:12px;color:#374151;cursor:pointer;
                     transition:all 0.15s;max-width:240px;overflow:hidden;
                     white-space:nowrap;text-overflow:ellipsis"
              @mouseenter="e => { e.currentTarget.style.background='#eef2ff'; e.currentTarget.style.borderColor='#c7d2fe' }"
              @mouseleave="e => { e.currentTarget.style.background='#f9fafb'; e.currentTarget.style.borderColor='#e5e7eb' }"
            >{{ tip.label }}</button>
          </div>
        </div>

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

      <div v-if="messages.length && promptTips.length" style="display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px">
        <button
          v-for="tip in promptTips" :key="tip.text"
          @click="sendTip(tip.text)"
          :disabled="isLoading"
          :title="tip.text"
          style="padding:4px 10px;background:#f3f4f6;border:1px solid #e5e7eb;
                 border-radius:999px;font-size:12px;color:#6b7280;cursor:pointer;
                 transition:all 0.15s;max-width:200px;overflow:hidden;
                 white-space:nowrap;text-overflow:ellipsis"
          @mouseenter="e => { e.currentTarget.style.background='#eef2ff'; e.currentTarget.style.color='#4f46e5' }"
          @mouseleave="e => { e.currentTarget.style.background='#f3f4f6'; e.currentTarget.style.color='#6b7280' }"
        >{{ tip.label }}</button>
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
import { ref, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../store/chat'
import { useAuthStore } from '../store/auth'
import { storeToRefs } from 'pinia'
import NavBar from '../components/NavBar.vue'

const chatStore = useChatStore()
const { messages, isLoading, lastCanceled, thinkingLabel } = storeToRefs(chatStore)
const auth = useAuthStore()

const question = ref('')
const sessionId = ref('user-001')
const chatBox = ref(null)
const customers = ref([])
const promptTips = ref([])

// 客户零件面板
const activeCustomer = ref(null)
const customerParts = ref(null)
const partsLoading = ref(false)

function buildTips(hints) {
  return hints.map(h => {
    const proc = h.process ? `（${h.process}）` : ''
    return {
      label: [h.customer, h.part_name, h.process, h.inspection_item].filter(Boolean).join(' · '),
      text:  `${h.customer} ${h.part_name}${proc} ${h.inspection_item}的检验标准是什么`,
    }
  })
}

onMounted(async () => {
  // 客户列表
  try {
    const resp = await fetch('/api/v1/upload/customers')
    customers.value = (await resp.json()).customers || []
  } catch (_) {}

  // 提示词
  try {
    const resp = await fetch('/api/v1/upload/prompt-hints')
    const data = await resp.json()
    promptTips.value = buildTips(data.hints || [])
  } catch (_) {
    promptTips.value = []
  }
})

async function toggleCustomer(name) {
  if (activeCustomer.value === name) {
    // 再次点击同一客户，收起面板
    activeCustomer.value = null
    customerParts.value = null
    return
  }
  activeCustomer.value = name
  customerParts.value = null
  partsLoading.value = true
  try {
    const resp = await fetch(`/api/v1/upload/customers/${encodeURIComponent(name)}/parts`)
    const data = await resp.json()
    customerParts.value = data.parts || []
  } catch (_) {
    customerParts.value = []
  } finally {
    partsLoading.value = false
  }
}

async function deleteSip(documentId, partName) {
  if (!confirm(`确定要删除 "${partName}" (${documentId}) 的全部 SIP 记录吗？此操作不可撤销。`)) return
  try {
    const resp = await fetch(`/api/v1/upload/sip/${encodeURIComponent(documentId)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${auth.token}` },
    })
    if (!resp.ok) {
      const data = await resp.json()
      alert(`删除失败: ${data.detail || resp.status}`)
      return
    }
    // 从当前列表中移除已删除的条目
    customerParts.value = customerParts.value.filter(p => p.document_id !== documentId)
    // 若该客户下已无记录，刷新客户列表并收起面板
    if (customerParts.value.length === 0) {
      activeCustomer.value = null
      customerParts.value = null
      const resp2 = await fetch('/api/v1/upload/customers')
      customers.value = (await resp2.json()).customers || []
    }
  } catch (e) {
    alert(`删除失败: ${e.message}`)
  }
}

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

function sendTip(text) {
  if (isLoading.value) return
  question.value = text
  sendMessage()
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
