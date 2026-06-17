import { defineStore } from 'pinia'
import axios from 'axios'
import { marked } from 'marked'
import { chatApi } from '../api/chat'

marked.setOptions({ breaks: true })

function renderMarkdown(text) {
  return marked.parse(text || '')
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    sessionId: 'user-001',
    isLoading: false,
    lastCanceled: false,
    _controller: null
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
    async sendMessage(question) {
      this.isLoading = true
      this.lastCanceled = false
      this.messages.push({ role: 'user', content: question })

      const controller = new AbortController()
      this._controller = controller

      try {
        const response = await chatApi.query(question, this.sessionId, controller.signal)
        this._renderResponse(response.data)
        if (response.data.cancelled) {
          this.lastCanceled = true
        }
      } catch (error) {
        if (axios.isCancel(error) || error.name === 'CanceledError') {
          this.messages.push({ role: 'assistant', content: '⏸ 已停止。可以「继续上次」或换一个新问题。', isCanceled: true })
          this.lastCanceled = true
        } else {
          this.messages.push({ role: 'assistant', content: `❌ 请求失败: ${error.message}`, isError: true })
        }
      } finally {
        this.isLoading = false
        this._controller = null
      }
    },
    async cancelCurrent() {
      if (!this.isLoading) return
      // 同时请求后端取消 + 中止前端 HTTP，确保 UI 立即解锁
      try {
        await chatApi.cancel(this.sessionId)
      } catch (e) {
        // 即使后端取消失败，仍然中止前端请求
      }
      if (this._controller) {
        this._controller.abort()
      }
    },
    async resumeLast() {
      if (this.isLoading) return
      this.isLoading = true
      this.lastCanceled = false

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
      this.messages = []
      this.lastCanceled = false
    }
  }
})
