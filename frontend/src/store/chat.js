import { defineStore } from 'pinia'
import axios from 'axios'
import { marked } from 'marked'
import { chatApi } from '../api/chat'

marked.setOptions({ breaks: true })

function renderMarkdown(text) {
  return marked.parse(text || '')
}

// HTML 转义（打字机动画期间安全显示纯文本）
function escapeHtml(text) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    sessionId: 'user-001',
    isLoading: false,
    isTyping: false,       // 打字机动画进行中
    thinkingLabel: '正在思考...',
    lastCanceled: false,
    _controller: null,
    _typewriterTimer: null,
  }),
  actions: {
    _renderResponse(data) {
      if (data.cancelled) {
        this.messages.push({ role: 'assistant', content: '⏸ 已停止。可以「继续上次」或换一个新问题。', isCanceled: true })
        return
      }
      if (data.error) {
        this.messages.push({ role: 'assistant', content: `❌ 错误: ${data.error}`, isError: true })
        return
      }
      let answer = renderMarkdown(data.answer || '')
      if (data.pdf_urls && data.pdf_urls.length > 0) {
        const pdfs = data.pdf_urls.map(url =>
          `<a href="/${url}" target="_blank">📥 ${url}</a>`
        ).join('')
        answer += `<div class="pdf-links">📄 相关文档: ${pdfs}</div>`
      }
      this.messages.push({ role: 'assistant', content: answer })
    },

    _startTypewriter(msgIndex, rawText, pdfUrls) {
      const BATCH = 4       // 每帧显示字符数
      const INTERVAL = 16   // ms（≈60fps），约 250 字/秒

      this.isTyping = true
      let charIndex = 0

      this._typewriterTimer = setInterval(() => {
        charIndex = Math.min(charIndex + BATCH, rawText.length)
        const slice = rawText.slice(0, charIndex)
        this.messages[msgIndex].content = escapeHtml(slice)

        if (charIndex >= rawText.length) {
          clearInterval(this._typewriterTimer)
          this._typewriterTimer = null

          // 动画结束后渲染完整 Markdown
          let finalContent = renderMarkdown(rawText)
          if (pdfUrls && pdfUrls.length > 0) {
            const pdfs = pdfUrls.map(url =>
              `<a href="/${url}" target="_blank">📥 ${url}</a>`
            ).join('')
            finalContent += `<div class="pdf-links">📄 相关文档: ${pdfs}</div>`
          }
          this.messages[msgIndex].content = finalContent
          this.isTyping = false
        }
      }, INTERVAL)
    },

    async sendMessage(question) {
      if (this.isLoading || this.isTyping) return
      this.isLoading = true
      this.lastCanceled = false
      this.thinkingLabel = '正在思考...'
      this.messages.push({ role: 'user', content: question })

      const controller = new AbortController()
      this._controller = controller

      try {
        await chatApi.queryStream(
          question,
          this.sessionId,
          // onThinking
          (event) => {
            this.thinkingLabel = event.label
          },
          // onDone
          (event) => {
            this.isLoading = false
            this._controller = null

            if (event.cancelled) {
              this.messages.push({ role: 'assistant', content: '⏸ 已停止。可以「继续上次」或换一个新问题。', isCanceled: true })
              this.lastCanceled = true
              return
            }

            const rawText = event.answer || ''
            const pdfUrls = event.pdf_urls || []

            // 先插入空消息占位，打字机逐步填充
            const msgIndex = this.messages.length
            this.messages.push({ role: 'assistant', content: '' })
            this._startTypewriter(msgIndex, rawText, pdfUrls)
          },
          // onError
          (error) => {
            this.isLoading = false
            this._controller = null
            this.messages.push({ role: 'assistant', content: `❌ 请求失败: ${error}`, isError: true })
          },
          controller.signal,
        )
      } catch (error) {
        this.isLoading = false
        this._controller = null
        if (error.name === 'AbortError') {
          this.messages.push({ role: 'assistant', content: '⏸ 已停止。可以「继续上次」或换一个新问题。', isCanceled: true })
          this.lastCanceled = true
        } else {
          this.messages.push({ role: 'assistant', content: `❌ 请求失败: ${error.message}`, isError: true })
        }
      }
    },

    async cancelCurrent() {
      if (!this.isLoading) return
      try {
        await chatApi.cancel(this.sessionId)
      } catch (e) {}
      if (this._controller) {
        this._controller.abort()
      }
    },

    async resumeLast() {
      if (this.isLoading) return
      this.isLoading = true
      this.lastCanceled = false
      this.thinkingLabel = '正在恢复上次查询...'

      const controller = new AbortController()
      this._controller = controller

      try {
        const response = await chatApi.resume(this.sessionId, controller.signal)
        this._renderResponse(response.data)
        if (response.data.cancelled) {
          this.lastCanceled = true
        }
      } catch (error) {
        if (axios.isCancel(error) || error.name === 'CanceledError') {
          this.messages.push({ role: 'assistant', content: '⏸ 已停止。可以「继续上次」或换一个新问题。', isCanceled: true })
          this.lastCanceled = true
        } else {
          this.messages.push({ role: 'assistant', content: `❌ 继续失败: ${error.message}`, isError: true })
        }
      } finally {
        this.isLoading = false
        this._controller = null
      }
    },

    clearChat() {
      if (this._typewriterTimer) {
        clearInterval(this._typewriterTimer)
        this._typewriterTimer = null
      }
      this.messages = []
      this.lastCanceled = false
      this.isTyping = false
    }
  }
})
