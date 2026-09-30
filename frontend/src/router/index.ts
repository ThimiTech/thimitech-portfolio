import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../pages/LandingPage.vue'
import DetailPage from "../pages/DetailPage.vue"
import ApplyPage from '../pages/ApplyPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: LandingPage },
    {path: "/projects/:id",name: "project-detail", component: DetailPage },
    { path: '/apply/:jobId', name: 'apply', component: ApplyPage },
  ],
})

export default router