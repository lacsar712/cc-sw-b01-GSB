import { createRouter, createWebHistory } from 'vue-router'
import HomeView from './views/HomeView.vue'
import JobDetailView from './views/JobDetailView.vue'
import ReworkView from './views/ReworkView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomeView },
    { path: '/rework', name: 'rework', component: ReworkView },
    { path: '/jobs/:id', name: 'job-detail', component: JobDetailView, props: true },
  ],
})

export default router
