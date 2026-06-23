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

      <!-- ① Excel 导入 -->
      <div class="card" style="margin-bottom:24px">
        <h2>📊 导入检验数据（Excel）</h2>
        <p style="color:#666;margin-bottom:20px">
          上传包含 12 列的 SIP 检验记录 Excel，批量写入数据库。<br>
          <span style="font-size:12px;color:#999">
            列顺序：项目号 | 客户 | 文件号 | 零件号 | 零件名称 | 工序 | 模具号 | 检验项 | 规范或描述 | 检验方法 | 检查频次 | 版本号
          </span>
        </p>

        <div style="border:2px dashed #ddd;border-radius:12px;padding:32px;text-align:center;margin-bottom:16px">
          <input type="file" accept=".xlsx,.xls" @change="handleExcelSelect" style="display:none" ref="excelInput">
          <button class="btn-secondary" @click="$refs.excelInput.click()">选择 Excel 文件</button>
          <p style="margin-top:8px;color:#999;font-size:13px">支持 .xlsx / .xls</p>
        </div>

        <div v-if="excelFile">
          <div style="padding:10px;background:#f8f8f8;border-radius:6px;margin-bottom:12px">
            📄 {{ excelFile.name }} — {{ (excelFile.size / 1024).toFixed(1) }} KB
          </div>
          <button @click="uploadExcel" :disabled="excelUploading"
            style="padding:12px 24px;background:#667eea;color:white;border:none;border-radius:8px;cursor:pointer"
            :style="excelUploading ? 'opacity:0.6;cursor:not-allowed' : ''">
            {{ excelUploading ? '导入中...' : '开始导入' }}
          </button>
        </div>

        <div v-if="excelResult" style="margin-top:16px;padding:14px;border-radius:8px"
          :style="excelResult.success ? 'background:#f0fdf4;border:1px solid #86efac' : 'background:#fef2f2;border:1px solid #fca5a5'">
          <div style="font-weight:bold;margin-bottom:6px">
            {{ excelResult.success ? '✅ 导入完成' : '❌ 导入失败' }}
          </div>
          <div style="font-size:14px;color:#555">
            新增：<b>{{ excelResult.inserted }}</b> 条 &nbsp;|&nbsp;
            更新：<b>{{ excelResult.updated }}</b> 条 &nbsp;|&nbsp;
            跳过：<b>{{ excelResult.skipped }}</b> 条 &nbsp;|&nbsp;
            错误：<b>{{ excelResult.errors }}</b> 条
          </div>
          <div v-if="excelResult.error_details && excelResult.error_details.length"
            style="margin-top:8px;font-size:12px;color:#dc2626">
            <div v-for="(e, i) in excelResult.error_details" :key="i">{{ e }}</div>
          </div>
        </div>
      </div>

      <!-- ② PDF 上传 -->
      <div class="card">
        <h2>📄 上传 SIP 文件（PDF）</h2>
        <p style="color:#666;margin-bottom:20px">
          上传 SIP PDF 文件，系统自动识别文件号并以 <code>{文件号}.pdf</code> 保存到文档库。
          若自动识别失败，可手动输入文件号后重试。
        </p>

        <div style="border:2px dashed #ddd;border-radius:12px;padding:32px;text-align:center;margin-bottom:16px">
          <input type="file" accept=".pdf" multiple @change="handlePdfSelect" style="display:none" ref="pdfInput">
          <button class="btn-secondary" @click="$refs.pdfInput.click()">选择 PDF 文件</button>
          <p style="margin-top:8px;color:#999;font-size:13px">支持多选 .pdf，逐个上传</p>
        </div>

        <div v-if="pdfFiles.length">
          <div v-for="(pf, i) in pdfFiles" :key="i"
            style="padding:10px 12px;background:#f8f8f8;border-radius:8px;margin-bottom:10px">
            <div style="display:flex;align-items:center;gap:12px">
              <span style="flex:1;font-size:13px">📄 {{ pf.file.name }} — {{ (pf.file.size / 1024).toFixed(1) }} KB</span>
              <span v-if="pf.status === 'pending'" style="color:#999;font-size:12px">待上传</span>
              <span v-else-if="pf.status === 'uploading'" style="color:#667eea;font-size:12px">上传中...</span>
              <span v-else-if="pf.status === 'ok'" style="color:#16a34a;font-size:12px">
                ✅ {{ pf.document_id }}.pdf{{ pf.overwritten ? '（已覆盖）' : '' }}
                <span v-if="pf.extracted_by === 'manual'" style="color:#9ca3af">（手动）</span>
              </span>
              <span v-else style="color:#dc2626;font-size:12px">❌ {{ pf.errorMsg }}</span>
            </div>

            <!-- 识别失败时显示手动输入区 -->
            <div v-if="pf.status === 'error'" style="margin-top:8px;display:flex;gap:8px;align-items:center">
              <div v-if="pf.snippet" style="font-size:11px;color:#6b7280;margin-bottom:6px;line-height:1.4">
                PDF 文本片段：{{ pf.snippet.slice(0, 100) }}…
              </div>
            </div>
            <div v-if="pf.status === 'error'" style="margin-top:6px;display:flex;gap:8px;align-items:center">
              <input v-model="pf.manualId" placeholder="手动输入文件号，如 VHST-SIP-SA2HG-008"
                style="flex:1;padding:6px 10px;border:1px solid #d1d5db;border-radius:6px;font-size:13px">
              <button @click="retryPdf(pf)" :disabled="!pf.manualId || pf.status === 'uploading'"
                style="padding:6px 14px;background:#667eea;color:white;border:none;border-radius:6px;cursor:pointer;font-size:13px;white-space:nowrap">
                重试
              </button>
            </div>
          </div>

          <button @click="uploadPdfs" :disabled="pdfUploading || allPdfsDone"
            style="margin-top:10px;padding:12px 24px;background:#667eea;color:white;border:none;border-radius:8px;cursor:pointer"
            :style="(pdfUploading || allPdfsDone) ? 'opacity:0.6;cursor:not-allowed' : ''">
            {{ pdfUploading ? '上传中...' : `上传 ${pendingPdfCount} 个文件` }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

// ---- Excel ----
const excelFile = ref(null)
const excelInput = ref(null)
const excelUploading = ref(false)
const excelResult = ref(null)

function handleExcelSelect(e) {
  excelFile.value = e.target.files[0] || null
  excelResult.value = null
}

async function uploadExcel() {
  if (!excelFile.value || excelUploading.value) return
  excelUploading.value = true
  excelResult.value = null
  const fd = new FormData()
  fd.append('file', excelFile.value)
  try {
    const resp = await fetch('/api/v1/upload/excel', { method: 'POST', body: fd })
    const data = await resp.json()
    excelResult.value = resp.ok
      ? data
      : { success: false, inserted: 0, skipped: 0, errors: 1, error_details: [data.detail || '上传失败'] }
  } catch (e) {
    excelResult.value = { success: false, inserted: 0, skipped: 0, errors: 1, error_details: [String(e)] }
  } finally {
    excelUploading.value = false
  }
}

// ---- PDF ----
// pf 结构: { file, status: 'pending'|'uploading'|'ok'|'error', document_id, overwritten, extracted_by, errorMsg, snippet, manualId }
const pdfFiles = ref([])
const pdfInput = ref(null)
const pdfUploading = ref(false)

const pendingPdfCount = computed(() => pdfFiles.value.filter(p => p.status === 'pending').length)
const allPdfsDone = computed(() => pdfFiles.value.length > 0 && pdfFiles.value.every(p => p.status === 'ok'))

function handlePdfSelect(e) {
  pdfFiles.value = Array.from(e.target.files).map(f => ({
    file: f, status: 'pending', document_id: '', overwritten: false,
    extracted_by: '', errorMsg: '', snippet: '', manualId: '',
  }))
}

async function _uploadOnePdf(pf, manualId = null) {
  pf.status = 'uploading'
  const fd = new FormData()
  fd.append('file', pf.file)
  if (manualId) fd.append('document_id', manualId)
  try {
    const resp = await fetch('/api/v1/upload/pdf', { method: 'POST', body: fd })
    const data = await resp.json()
    if (resp.ok && data.success) {
      pf.status = 'ok'
      pf.document_id = data.document_id
      pf.overwritten = data.overwritten
      pf.extracted_by = data.extracted_by
    } else {
      pf.status = 'error'
      // detail 可能是字符串或对象
      const detail = data.detail
      if (detail && typeof detail === 'object') {
        pf.errorMsg = detail.message || '识别失败'
        pf.snippet = detail.snippet || ''
      } else {
        pf.errorMsg = detail || '上传失败'
        pf.snippet = ''
      }
    }
  } catch (e) {
    pf.status = 'error'
    pf.errorMsg = String(e)
  }
}

async function uploadPdfs() {
  if (!pdfFiles.value.length || pdfUploading.value) return
  pdfUploading.value = true
  for (const pf of pdfFiles.value) {
    if (pf.status !== 'pending') continue
    await _uploadOnePdf(pf)
  }
  pdfUploading.value = false
}

async function retryPdf(pf) {
  const id = pf.manualId.trim()
  if (!id) return
  await _uploadOnePdf(pf, id)
}
</script>
