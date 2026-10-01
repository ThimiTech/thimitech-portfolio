import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../pages/LandingPage.vue'
import ApplyPage from '../pages/ApplyPage.vue'
import DetailPage from '../pages/DetailPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/projects/:id', name: 'projects', component: DetailPage},
    { path: '/', name: 'home', component: LandingPage },
    { path: '/apply/:jobId', name: 'apply', component: ApplyPage },
    
    
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router