import { createRouter, createWebHistory } from 'vue-router'
import Chat from '../views/Chat.vue'
import Upload from '../views/Upload.vue'
import Knowledge from '../views/Knowledge.vue'
import Monitor from '../views/Monitor.vue'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', name: 'Chat', component: Chat },
  { path: '/upload', name: 'Upload', component: Upload },
  { path: '/knowledge', name: 'Knowledge', component: Knowledge },
  { path: '/monitor', name: 'Monitor', component: Monitor }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router