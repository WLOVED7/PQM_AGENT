<template>
  <div class="nav">
    <h1>🔥 热压品质异常预测系统</h1>
    <div class="nav-links">
      <router-link to="/chat">💬 对话</router-link>
      <template v-if="auth.isAdmin">
        <router-link to="/upload">📤 上传</router-link>
        <router-link to="/knowledge">📚 知识库</router-link>
        <router-link to="/monitor">📊 监控</router-link>
        <button class="nav-logout-btn" @click="handleLogout">退出登录</button>
      </template>
      <template v-else>
        <router-link to="/login">🔐 管理员</router-link>
      </template>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'

const auth = useAuthStore()
const router = useRouter()

function handleLogout() {
  auth.logout()
  router.push('/chat')
}
</script>

<style scoped>
.nav-logout-btn {
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
}
.nav-logout-btn:hover {
  background: rgba(255, 255, 255, 0.25);
}
</style>
