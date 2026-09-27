<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { api } from '../api.js'

const role = ref(localStorage.getItem('role') || '')
const jobs = ref([])
const events = ref([])
const edits = ref({})
const err = ref('')
const ok = ref('')
const detail = ref(null)
const detailEvents = ref([])
let timer

const STATUS_LABEL = { pending: '待处理', claimed: '领取中', done: '已结案' }

const pendingJobs = computed(() => jobs.value.filter((j) => j.status === 'pending'))
const claimedJobs = computed(() => jobs.value.filter((j) => j.status === 'claimed'))

// 重投履历按任务分块（块内按时间正序）
const eventBlocks = computed(() => {
  const map = new Map()
  for (const e of events.value) {
    if (!map.has(e.job_id)) {
      map.set(e.job_id, { job_id: e.job_id, lamp: e.lamp, nominal_nm: e.nominal_nm, items: [] })
    }
    map.get(e.job_id).items.unshift(e)
  }
  return [...map.values()]
})

function syncEdits() {
  for (const j of jobs.value) {
    if (j.status === 'pending' && edits.value[j.id] === undefined) {
      edits.value[j.id] = j.measured_nm
    }
  }
}

async function refresh() {
  if (!localStorage.getItem('tok')) return
  try {
    const [jobRows, eventRows] = await Promise.all([api('/api/jobs'), api('/api/events')])
    jobs.value = jobRows
    events.value = eventRows
    syncEdits()
    err.value = ''
  } catch (e) {
    err.value = String(e.message || e)
  }
}

async function resubmit(job) {
  err.value = ''
  ok.value = ''
  const v = Number(edits.value[job.id])
  if (!Number.isFinite(v)) {
    err.value = `任务 #${job.id} 的实测波长无效`
    return
  }
  try {
    const r = await api(`/api/jobs/${job.id}/resubmit`, {
      method: 'POST',
      body: JSON.stringify({ measured_nm: v }),
    })
    ok.value = `任务 #${job.id} 已改实测重投：${r.old_measured_nm} → ${r.new_measured_nm} nm`
    delete edits.value[job.id]
    await refresh()
  } catch (e) {
    err.value = String(e.message || e)
    await refresh()
  }
}

async function openDetail(job) {
  err.value = ''
  try {
    const [j, ev] = await Promise.all([
      api(`/api/jobs/${job.id}`),
      api(`/api/jobs/${job.id}/events`),
    ])
    detail.value = j
    detailEvents.value = ev
  } catch (e) {
    err.value = String(e.message || e)
  }
}

function closeDetail() {
  detail.value = null
  detailEvents.value = []
}

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? String(t) : d.toLocaleString()
}

onMounted(() => {
  role.value = localStorage.getItem('role') || ''
  refresh()
  timer = setInterval(refresh, 1000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div>
    <h2>重投台</h2>
    <p v-if="err" style="color:#b00020">{{ err }}</p>
    <p v-if="ok" style="color:#1a7f37">{{ ok }}</p>

    <section style="margin:16px 0; padding:12px; border:1px solid #ccc;">
      <h3>待处理（排队中可改实测后重投）</h3>
      <p v-if="!pendingJobs.length" class="hint">暂无待处理任务</p>
      <table v-else border="1" cellpadding="6" style="border-collapse:collapse; width:100%;">
        <thead>
          <tr>
            <th>编号</th><th>灯种</th><th>标称</th><th>实测</th><th>状态</th><th>改实测区</th><th>详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="j in pendingJobs" :key="j.id">
            <td>{{ j.id }}</td>
            <td>{{ j.lamp }}</td>
            <td>{{ j.nominal_nm }}</td>
            <td>{{ j.measured_nm }}</td>
            <td>{{ STATUS_LABEL[j.status] || j.status }}</td>
            <td>
              <template v-if="role === 'writer'">
                <input
                  type="number"
                  step="0.01"
                  style="width:110px"
                  v-model.number="edits[j.id]"
                />
                <button type="button" @click="resubmit(j)">确认重投</button>
              </template>
              <span v-else class="hint">巡检员只读，不可改实测</span>
            </td>
            <td><button type="button" @click="openDetail(j)">详情</button></td>
          </tr>
        </tbody>
      </table>
    </section>

    <section v-if="claimedJobs.length" style="margin:16px 0; padding:12px; border:1px solid #ccc;">
      <h3>领取中（不可改实测）</h3>
      <ul style="margin:0; padding-left:18px;">
        <li v-for="j in claimedJobs" :key="j.id">
          #{{ j.id }} {{ j.lamp }}（标称 {{ j.nominal_nm }} nm / 实测 {{ j.measured_nm }} nm）领取中，不可改实测
        </li>
      </ul>
    </section>

    <section style="margin:16px 0; padding:12px; border:1px solid #ccc;">
      <h3>重投履历</h3>
      <p v-if="!eventBlocks.length" class="hint">暂无重投履历</p>
      <div
        v-for="b in eventBlocks"
        :key="b.job_id"
        style="margin:8px 0; padding:8px; border:1px solid #ddd; background:#fafafa;"
      >
        <strong>任务 #{{ b.job_id }} · {{ b.lamp }}</strong>
        <span class="hint">（标称 {{ b.nominal_nm }} nm）</span>
        <ul style="margin:6px 0 0; padding-left:18px;">
          <li v-for="e in b.items" :key="e.id">
            改前 {{ e.old_measured_nm }} nm → 改后 {{ e.new_measured_nm }} nm
            ｜ 操作人 {{ e.actor }} ｜ {{ fmtTime(e.created_at) }}
          </li>
        </ul>
      </div>
    </section>

    <div
      v-if="detail"
      style="position:fixed; inset:0; background:rgba(0,0,0,0.35); z-index:200; display:flex; align-items:center; justify-content:center;"
      @click.self="closeDetail"
    >
      <div style="background:#fff; padding:16px; border:1px solid #888; width:420px; max-height:80vh; overflow:auto;">
        <h3>任务详情 #{{ detail.id }}</h3>
        <p>灯种：{{ detail.lamp }}</p>
        <p>标称 nm：{{ detail.nominal_nm }}</p>
        <p>实测 nm：{{ detail.measured_nm }}</p>
        <p>状态：{{ STATUS_LABEL[detail.status] || detail.status }}</p>
        <p>结论：{{ detail.verdict }}</p>
        <p>理由：{{ detail.reason }}</p>
        <h4>重投履历</h4>
        <p v-if="!detailEvents.length" class="hint">暂无重投履历</p>
        <ul v-else style="margin:0; padding-left:18px;">
          <li v-for="e in detailEvents" :key="e.id">
            改前 {{ e.old_measured_nm }} nm → 改后 {{ e.new_measured_nm }} nm
            ｜ {{ e.actor }} ｜ {{ fmtTime(e.created_at) }}
          </li>
        </ul>
        <p style="text-align:right;"><button type="button" @click="closeDetail">关闭</button></p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hint {
  color: #666;
  font-size: 13px;
}
</style>
