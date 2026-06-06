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
  }
}
