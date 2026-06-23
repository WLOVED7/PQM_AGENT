<template>
  <div>
    <div class="nav">
      <h1>🔥 热压品质异常预测系统</h1>
      <div class="nav-links">
        <router-link to="/chat">💬 对话</router-link>
        <router-link to="/upload">📤 上传</router-link>
        <router-link to="/knowledge">📚 知识库</router-link>
        <router-link to="/monitor">📊 监控</router-link>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <h2>📚 知识库管理</h2>
        <p style="color:#666;margin-bottom:20px">查看和管理热压品质异常预测系统的文档</p>

        <div style="margin-bottom:20px">
          <input v-model="searchQuery" placeholder="搜索文档..." style="padding:10px 14px;border:1px solid #ddd;border-radius:6px;width:300px">
        </div>

        <div v-if="loading" class="loading">
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          加载中...
        </div>

        <div v-else-if="documents.length === 0" style="color:#999;text-align:center;padding:40px">
          暂无文档
        </div>

        <div v-else>
          <div v-for="doc in documents" :key="doc.document_id" style="padding:16px;border-bottom:1px solid #eee">
            <div style="font-weight:bold;color:#333">{{ doc.document_id }}</div>
            <div style="color:#666;font-size:13px;margin-top:5px">
              {{ doc.part_name || '' }} - 版本: {{ doc.version || 'N/A' }}
            </div>
            <div v-if="doc.project" style="color:#999;font-size:12px">项目: {{ doc.project }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const documents = ref([])
const searchQuery = ref('')
const loading = ref(false)

onMounted(async () => {
  loading.value = true
  try {
    const response = await fetch('/api/v1/documents')
    if (response.ok) {
      const data = await response.json()
      documents.value = data.documents || []
    }
  } catch (e) {
    console.error('Failed to load documents', e)
  } finally {
    loading.value = false
  }
})
</script>