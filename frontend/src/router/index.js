import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'
import Chat from '../views/Chat.vue'
import Upload from '../views/Upload.vue'
import Knowledge from '../views/Knowledge.vue'
import Monitor from '../views/Monitor.vue'
import Login from '../views/Login.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/chat', name: 'Chat', component: Chat },
  { path: '/upload', name: 'Upload', component: Upload, meta: { requiresAdmin: true } },
  { path: '/knowledge', name: 'Knowledge', component: Knowledge, meta: { requiresAdmin: true } },
  { path: '/monitor', name: 'Monitor', component: Monitor, meta: { requiresAdmin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAdmin && !auth.isAdmin) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
})

export default router
