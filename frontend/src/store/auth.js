import { defineStore } from 'pinia'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('admin_token') || null,
  }),
  getters: {
    isAdmin: (state) => !!state.token,
  },
  actions: {
    async login(username, password) {
      const resp = await fetch('/api/v1/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      })
      if (!resp.ok) {
        const data = await resp.json()
        throw new Error(data.detail || '登录失败')
      }
      const { access_token } = await resp.json()
      this.token = access_token
      localStorage.setItem('admin_token', access_token)
    },
    logout() {
      this.token = null
      localStorage.removeItem('admin_token')
    },
  },
})
