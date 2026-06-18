import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 120000
})

export const chatApi = {
  query(question, sessionId = 'user-001', signal = undefined) {
    return api.post('/agent/query', { question, session_id: sessionId }, { signal })
  },
  cancel(sessionId) {
    return api.post(`/agent/cancel/${sessionId}`)
  },
  resume(sessionId, signal = undefined) {
    return api.post(`/agent/resume/${sessionId}`, null, { signal })
  },
  getHistory(sessionId, limit = 20) {
    return api.get(`/agent/history/${sessionId}?limit=${limit}`)
  },

  /**
   * 流式查询 - SSE
   * @param {string} question
   * @param {string} sessionId
   * @param {function} onThinking  - ({ step, label }) => void
   * @param {function} onDone      - (eventData) => void
   * @param {function} onError     - (errorMsg) => void
   * @param {AbortSignal} signal
   */
  async queryStream(question, sessionId = 'user-001', onThinking, onDone, onError, signal) {
    let response
    try {
      response = await fetch('/api/v1/agent/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, session_id: sessionId }),
        signal,
      })
    } catch (err) {
      throw err
    }

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop()  // 保留未完整的行

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'thinking') {
            onThinking && onThinking(event)
          } else if (event.type === 'done') {
            onDone && onDone(event)
            return
          } else if (event.type === 'error') {
            onError && onError(event.error || '未知错误')
            return
          }
        } catch (_) {}
      }
    }
  }
}
