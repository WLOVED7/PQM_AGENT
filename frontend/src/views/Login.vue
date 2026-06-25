<template>
  <div>
    <NavBar />
    <div class="container">
      <div class="card" style="max-width:420px;margin:80px auto">
        <h2 style="margin-bottom:24px;text-align:center">🔐 管理员登录</h2>
        <div v-if="errorMsg" style="padding:10px 14px;background:#fef2f2;border:1px solid #fca5a5;
             border-radius:8px;color:#dc2626;font-size:13px;margin-bottom:16px">
          {{ errorMsg }}
        </div>
        <div style="margin-bottom:14px">
          <input v-model="username" placeholder="用户名" type="text"
            style="width:100%;padding:12px 14px;border:1px solid #d1d5db;border-radius:8px;
                   font-size:14px;outline:none"
            @keypress.enter="doLogin"
          >
        </div>
        <div style="margin-bottom:20px">
          <input v-model="password" placeholder="密码" type="password"
            style="width:100%;padding:12px 14px;border:1px solid #d1d5db;border-radius:8px;
                   font-size:14px;outline:none"
            @keypress.enter="doLogin"
          >
        </div>
        <button @click="doLogin" :disabled="loading"
          style="width:100%;padding:13px;background:#667eea;color:white;border:none;
                 border-radius:8px;font-size:15px;cursor:pointer;transition:background 0.3s"
          :style="loading ? 'opacity:0.6;cursor:not-allowed' : ''"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>
        <div style="margin-top:16px;text-align:center;font-size:13px;color:#6b7280">
          <router-link to="/chat" style="color:#667eea;text-decoration:none">
            作为普通用户访问对话页
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../store/auth'
import NavBar from '../components/NavBar.vue'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function doLogin() {
  if (!username.value || !password.value) return
  loading.value = true
  errorMsg.value = ''
  try {
    await auth.login(username.value, password.value)
    const redirect = route.query.redirect || '/upload'
    router.push(redirect)
  } catch (e) {
    errorMsg.value = e.message
  } finally {
    loading.value = false
  }
}
</script>
