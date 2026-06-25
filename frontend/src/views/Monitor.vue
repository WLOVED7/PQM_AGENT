<template>
  <div>
    <NavBar />

    <div class="container">
      <div class="card">
        <h2>📊 系统监控</h2>
        <p style="color:#666;margin-bottom:20px">查看系统运行状态和性能指标</p>

        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px;margin-bottom:30px">
          <div style="background:#f8f8f8;padding:20px;border-radius:8px;text-align:center">
            <div style="font-size:32px;color:#667eea;font-weight:bold">{{ stats.queries || 0 }}</div>
            <div style="color:#666;font-size:13px">总查询数</div>
          </div>
          <div style="background:#f8f8f8;padding:20px;border-radius:8px;text-align:center">
            <div style="font-size:32px;color:#667eea;font-weight:bold">{{ stats.sessions || 0 }}</div>
            <div style="color:#666;font-size:13px">活跃会话</div>
          </div>
          <div style="background:#f8f8f8;padding:20px;border-radius:8px;text-align:center">
            <div style="font-size:32px;color:#667eea;font-weight:bold">{{ stats.documents || 0 }}</div>
            <div style="color:#666;font-size:13px">文档总数</div>
          </div>
        </div>

        <h3 style="margin-bottom:15px">最近查询</h3>
        <div v-if="recentQueries.length === 0" style="color:#999;text-align:center;padding:30px">
          暂无查询记录
        </div>
        <div v-else>
          <div v-for="(q, i) in recentQueries" :key="i" style="padding:12px;background:#f8f8f8;border-radius:6px;margin-bottom:8px;font-size:14px">
            <span style="color:#667eea">{{ q.time }}</span> - {{ q.question }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../components/NavBar.vue'

const stats = ref({})
const recentQueries = ref([])

onMounted(async () => {
  try {
    const response = await fetch('/api/v1/monitor/stats')
    if (response.ok) {
      stats.value = await response.json()
    }
  } catch (e) {
    console.error('Failed to load stats', e)
  }

  try {
    const response = await fetch('/api/v1/monitor/recent')
    if (response.ok) {
      recentQueries.value = await response.json()
    }
  } catch (e) {
    console.error('Failed to load recent queries', e)
  }
})
</script>