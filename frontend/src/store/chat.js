import { defineStore } from 'pinia'
import { chatApi } from '../api/chat'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],
    sessionId: 'user-001',
    isLoading: false
  }),
  actions: {
    async sendMessage(question) {
      this.isLoading = true
      this.messages.push({ role: 'user', content: question })

      try {
        const response = await chatApi.query(question, this.sessionId)
        const data = response.data

        if (data.error) {
          this.messages.push({ role: 'assistant', content: `❌ 错误: ${data.error}`, isError: true })
        } else {
          let answer = data.answer || ''
          if (data.pdf_urls && data.pdf_urls.length > 0) {
            const pdfs = data.pdf_urls.map(url =>
              `<a href="http://localhost:8000/${url}" target="_blank">📥 ${url}</a>`
            ).join('')
            answer += `<div class="pdf-links">📄 相关文档: ${pdfs}</div>`
          }
          this.messages.push({ role: 'assistant', content: answer })
        }
      } catch (error) {
        this.messages.push({ role: 'assistant', content: `❌ 请求失败: ${error.message}`, isError: true })
      } finally {
        this.isLoading = false
      }
    },
    clearChat() {
      this.messages = []
    }
  }
})