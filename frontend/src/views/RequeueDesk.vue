<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api.js'

const emit = defineEmits(['close'])

const role = ref(localStorage.getItem('role') || '')
const pendingJobs = ref([])
const selected = ref(null)
const logs = ref([])
const editMeasured = ref(null)
const err = ref('')
const notice = ref('')
let timer

const STATUS_LABEL = {
  pending: '待处理',
  processing: '领取中',
  done: '已结案',
}

const canEdit = computed(
  () => role.value === 'writer' && selected.value && selected.value.status === 'pending'
)

function statusLabel(s) {
  return STATUS_LABEL[s] || s
}

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? String(t) : d.toLocaleString()
}

async function refreshList() {
  try {
    const jobs = await api('/api/jobs')
    pendingJobs.value = jobs.filter((j) => j.status === 'pending')
    err.value = ''
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function refreshSelected() {
  if (!selected.value) return
  try {
    const [job, logRows] = await Promise.all([
      api(`/api/jobs/${selected.value.id}`),
      api(`/api/jobs/${selected.value.id}/requeue-logs`),
    ])
    selected.value = job
    logs.value = logRows
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function refresh() {
  if (!localStorage.getItem('tok')) return
  await refreshList()
  await refreshSelected()
}

async function pick(job) {
  err.value = ''
  notice.value = ''
  selected.value = { id: job.id }
  logs.value = []
  await refreshSelected()
  if (selected.value) editMeasured.value = selected.value.measured_nm
}

async function confirmRequeue() {
  err.value = ''
  notice.value = ''
  try {
    await api(`/api/jobs/${selected.value.id}/requeue`, {
      method: 'POST',
      body: JSON.stringify({ measured_nm: editMeasured.value }),
    })
    notice.value = '已改实测并重投，履历已留痕（改前 / 改后）'
    await refresh()
  } catch (e) {
    err.value = String(e.message || e)
    await refreshSelected()
  }
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="desk-overlay" @click.self="emit('close')">
    <div class="desk-panel">
      <header class="desk-head">
        <h2>重投台</h2>
        <span class="desk-sub">待处理任务可改实测后重投；领取中与已结案不可改</span>
        <button type="button" class="close-btn" @click="emit('close')">关闭</button>
      </header>

      <p v-if="err" class="err">{{ err }}</p>
      <p v-if="notice" class="notice">{{ notice }}</p>

      <section class="block">
        <h3>待处理（仍排队，未领取）</h3>
        <p v-if="!pendingJobs.length" class="hint">暂无待处理任务</p>
        <table v-else border="1" cellpadding="6" class="grid">
          <thead>
            <tr>
              <th>编号</th><th>灯种</th><th>标称</th><th>实测</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="j in pendingJobs"
              :key="j.id"
              :class="{ chosen: selected && selected.id === j.id }"
              class="row"
              @click="pick(j)"
            >
              <td>{{ j.id }}</td>
              <td>{{ j.lamp }}</td>
              <td>{{ j.nominal_nm }}</td>
              <td>{{ j.measured_nm }}</td>
              <td>{{ statusLabel(j.status) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <div v-if="selected && selected.id" class="detail-blocks">
        <section class="block">
          <h3>改实测区 — 任务 #{{ selected.id }}</h3>
          <p>灯种：{{ selected.lamp }}</p>
          <p>标称 nm：{{ selected.nominal_nm }}</p>
          <p>当前实测 nm：{{ selected.measured_nm }}</p>
          <p>
            状态：{{ statusLabel(selected.status) }}
            <template v-if="selected.status === 'done'">
              — 结论：{{ selected.verdict }}（{{ selected.reason }}）
            </template>
          </p>
          <div v-if="canEdit" class="edit-line">
            <label>
              新实测 nm
              <input type="number" step="0.01" v-model.number="editMeasured" />
            </label>
            <button type="button" @click="confirmRequeue">确认改实测并重投</button>
          </div>
          <p v-else-if="role !== 'writer'" class="hint">巡检员只读，可看重投履历，不可改实测。</p>
          <p v-else class="hint">任务{{ statusLabel(selected.status) }}，实测不可再改。</p>
        </section>

        <section class="block">
          <h3>重投履历</h3>
          <p v-if="!logs.length" class="hint">暂无重投履历</p>
          <table v-else border="1" cellpadding="6" class="grid">
            <thead>
              <tr>
                <th>时间</th><th>改前实测</th><th>改后实测</th><th>操作人</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="log in logs" :key="log.id">
                <td>{{ fmtTime(log.changed_at) }}</td>
                <td>{{ log.old_measured_nm }}</td>
                <td>{{ log.new_measured_nm }}</td>
                <td>{{ log.changed_by }}</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
      <p v-else class="hint">点击上方待处理行，在框内查看改实测区与重投履历。</p>
    </div>
  </div>
</template>

<style scoped>
.desk-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 48px 16px;
  overflow-y: auto;
}
.desk-panel {
  background: #fff;
  color: #1a2332;
  width: 100%;
  max-width: 880px;
  border-radius: 6px;
  padding: 16px 20px 24px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.35);
}
.desk-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  border-bottom: 1px solid #ddd;
  padding-bottom: 8px;
}
.desk-head h2 {
  margin: 0;
  font-size: 18px;
}
.desk-sub {
  flex: 1;
  color: #667;
  font-size: 13px;
}
.close-btn {
  cursor: pointer;
}
.block {
  margin: 14px 0;
  padding: 12px;
  border: 1px solid #ccc;
  border-radius: 4px;
}
.block h3 {
  margin-top: 0;
  font-size: 15px;
}
.grid {
  border-collapse: collapse;
  width: 100%;
}
.row {
  cursor: pointer;
}
.row:hover {
  background: #f0f6ff;
}
.row.chosen {
  background: #dceaff;
}
.detail-blocks {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}
.detail-blocks .block {
  flex: 1 1 340px;
}
.edit-line {
  display: flex;
  align-items: center;
  gap: 10px;
}
.edit-line button {
  cursor: pointer;
}
.hint {
  color: #667;
  font-size: 13px;
}
.err {
  color: #b00020;
}
.notice {
  color: #0a7a2f;
}
</style>
