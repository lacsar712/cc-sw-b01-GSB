<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api } from '../api.js'

const route = useRoute()
const router = useRouter()
const job = ref(null)
const events = ref([])
const err = ref('')

const STATUS_LABEL = { pending: '待处理', claimed: '领取中', done: '已结案' }

async function load() {
  err.value = ''
  job.value = null
  events.value = []
  try {
    job.value = await api(`/api/jobs/${route.params.id}`)
    events.value = await api(`/api/jobs/${route.params.id}/events`)
  } catch (e) {
    err.value = String(e.message || e)
  }
}

function fmtTime(t) {
  if (!t) return ''
  const d = new Date(t)
  return Number.isNaN(d.getTime()) ? String(t) : d.toLocaleString()
}

onMounted(load)
watch(() => route.params.id, load)
</script>

<template>
  <div>
    <p>
      <button type="button" @click="router.push('/')">返回总览</button>
    </p>
    <p v-if="err" style="color:#b00020">{{ err }}</p>
    <section v-if="job" style="margin:16px 0; padding:12px; border:1px solid #ccc;">
      <h3>任务详情 #{{ job.id }}</h3>
      <p>灯种：{{ job.lamp }}</p>
      <p>标称 nm：{{ job.nominal_nm }}</p>
      <p>实测 nm：{{ job.measured_nm }}</p>
      <p>状态：{{ STATUS_LABEL[job.status] || job.status }}</p>
      <p>结论：{{ job.verdict }}</p>
      <p>理由：{{ job.reason }}</p>
      <h4>重投履历</h4>
      <p v-if="!events.length" style="color:#666; font-size:13px;">暂无重投履历</p>
      <ul v-else style="margin:0; padding-left:18px;">
        <li v-for="e in events" :key="e.id">
          改前 {{ e.old_measured_nm }} nm → 改后 {{ e.new_measured_nm }} nm
          ｜ {{ e.actor }} ｜ {{ fmtTime(e.created_at) }}
        </li>
      </ul>
    </section>
  </div>
</template>
