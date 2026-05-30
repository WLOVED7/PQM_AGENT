<template>
  <div>
    <div class="nav">
      <h1>🔬 质量检验知识库</h1>
      <div class="nav-links">
        <router-link to="/chat">💬 对话</router-link>
        <router-link to="/upload">📤 上传</router-link>
        <router-link to="/knowledge">📚 知识库</router-link>
        <router-link to="/monitor">📊 监控</router-link>
      </div>
    </div>

    <div class="container">
      <div class="card">
        <h2>📤 上传 SIP 文档</h2>
        <p style="color:#666;margin-bottom:20px">支持批量上传 SIP (Standard Inspection Procedure) 文档</p>

        <div style="border:2px dashed #ddd;border-radius:12px;padding:40px;text-align:center;margin-bottom:20px">
          <input type="file" multiple accept=".pdf" @change="handleFileSelect" style="display:none" ref="fileInput">
          <button class="btn-secondary" @click="$refs.fileInput.click()">选择 PDF 文件</button>
          <p style="margin-top:10px;color:#999;font-size:13px">支持 .pdf 格式，可多选</p>
        </div>

        <div v-if="files.length > 0">
          <h3 style="margin-bottom:10px">已选择 {{ files.length }} 个文件:</h3>
          <div v-for="(f, i) in files" :key="i" style="padding:10px;background:#f8f8f8;border-radius:6px;margin-bottom:8px">
            {{ f.name }} - {{ (f.size / 1024).toFixed(1) }} KB
          </div>
          <button @click="uploadFiles" style="margin-top:10px;padding:12px 24px;background:#667eea;color:white;border:none;border-radius:8px;cursor:pointer">
            开始上传
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const files = ref([])
const fileInput = ref(null)

function handleFileSelect(e) {
  files.value = Array.from(e.target.files)
}

async function uploadFiles() {
  // TODO: 实现文件上传逻辑
  alert('上传功能开发中...')
}
</script>