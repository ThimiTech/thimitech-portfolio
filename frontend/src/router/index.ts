import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../pages/LandingPage.vue'
import ApplyPage from '../pages/ApplyPage.vue'
import DetailPage from '../pages/DetailPage.vue'
import { useAuth, type Role } from '../stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    /** Minimum role to enter. Inherited by children; the deepest match wins. */
    minRole?: Role
    /** Sidebar / topbar title (also sets document.title) */
    title?: string
    /** Signed-in users are sent on (to ?next or /app) instead of seeing this page */
    guestOnly?: boolean
  }
}

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/projects/:id', name: 'projects', component: DetailPage },
    { path: '/work', name: 'work', component: () => import('../pages/WorkPage.vue'), meta: { title: 'Our work' } },
    { path: '/work/:slug', name: 'work-detail', component: () => import('../pages/WorkDetailPage.vue') },
    { path: '/', name: 'home', component: LandingPage },
    { path: '/new', name: 'new-home', component: () => import('../pages/NewLandingPage.vue') },
    { path: '/apply/:jobId', name: 'apply', component: ApplyPage },
    { path: '/login', name: 'login', component: () => import('../pages/AuthPage.vue'), meta: { title: 'Sign in', guestOnly: true } },
    { path: '/register', name: 'register', component: () => import('../pages/AuthPage.vue'), meta: { title: 'Create account', guestOnly: true } },
    { path: '/forgot-password', name: 'forgot-password', component: () => import('../pages/AuthPage.vue'), meta: { title: 'Reset password' } },
    // not guestOnly: an emailed link must work even in a browser that is still signed in
    { path: '/reset-password', name: 'reset-password', component: () => import('../pages/AuthPage.vue'), meta: { title: 'Choose a new password' } },

    // Thimi Tech OS — internal platform
    {
      path: '/app',
      component: () => import('../layouts/AppLayout.vue'),
      meta: { minRole: 'employee' },
      children: [
        { path: '', name: 'app-dashboard', component: () => import('../pages/app/DashboardPage.vue'), meta: { title: 'Dashboard' } },
        { path: 'projects', name: 'app-projects', component: () => import('../pages/app/ProjectsPage.vue'), meta: { title: 'Projects' } },
        { path: 'projects/:id', name: 'app-project', component: () => import('../pages/app/ProjectPage.vue'), meta: { title: 'Project workspace' } },
        { path: 'finance', name: 'app-finance', component: () => import('../pages/app/FinancePage.vue'), meta: { title: 'Finance', minRole: 'hr_admin' } },
        { path: 'inventory', name: 'app-inventory', component: () => import('../pages/app/InventoryPage.vue'), meta: { title: 'Inventory', minRole: 'hr_admin' } },
        { path: 'monitoring', name: 'app-monitoring', component: () => import('../pages/app/MonitoringPage.vue'), meta: { title: 'Monitoring', minRole: 'super_admin' } },
        { path: 'audit', name: 'app-audit', component: () => import('../pages/app/AuditPage.vue'), meta: { title: 'Audit trail', minRole: 'super_admin' } },
        { path: 'my-pay', name: 'app-my-pay', component: () => import('../pages/app/MyPayPage.vue'), meta: { title: 'My pay' } },
        { path: 'my-pay/:id', name: 'app-my-payslip', component: () => import('../pages/app/MyPayslipPage.vue'), meta: { title: 'Payslip' } },
        { path: 'my-assets', name: 'app-my-assets', component: () => import('../pages/app/MyAssetsPage.vue'), meta: { title: 'My assets' } },
        { path: 'attendance', name: 'app-attendance', component: () => import('../pages/app/AttendancePage.vue'), meta: { title: 'Attendance' } },
        { path: 'leave', name: 'app-leave', component: () => import('../pages/app/LeavePage.vue'), meta: { title: 'Leave' } },
        { path: 'calendar', name: 'app-calendar', component: () => import('../pages/app/CalendarPage.vue'), meta: { title: 'Calendar' } },
        { path: 'notices', name: 'app-notices', component: () => import('../pages/app/NoticesPage.vue'), meta: { title: 'Notice board' } },
        { path: 'people', name: 'app-people', component: () => import('../pages/app/DirectoryPage.vue'), meta: { title: 'People' } },
        { path: 'people/:id', name: 'app-person', component: () => import('../pages/app/ProfilePage.vue'), meta: { title: 'Profile' } },
        { path: 'profile', name: 'app-profile', component: () => import('../pages/app/ProfilePage.vue'), meta: { title: 'My profile' } },
        { path: 'organization', name: 'app-organization', component: () => import('../pages/app/OrganizationPage.vue'), meta: { title: 'Organization' } },
        { path: ':pathMatch(.*)*', name: 'app-not-found', component: () => import('../pages/NotFoundPage.vue'), meta: { title: 'Page not found' } },
      ],
    },
    { path: '/:pathMatch(.*)*', name: 'not-found', component: () => import('../pages/NotFoundPage.vue'), meta: { title: 'Page not found' } },
  ],
  scrollBehavior(to, _from, savedPosition) {
    if (savedPosition) return savedPosition
    if (to.hash) return { el: to.hash, top: 88, behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' }
    return { top: 0 }
  },
})

router.beforeEach(async (to) => {
  const { isLoggedIn, user, fetchMe, hasRole } = useAuth()

  if (to.meta.guestOnly) {
    if (!isLoggedIn.value) return true
    if (!user.value) await fetchMe()
    if (!user.value) return true // stale token: let them sign in again
    const next = typeof to.query.next === 'string' && to.query.next.startsWith('/') && !to.query.next.startsWith('//') ? to.query.next : null
    return next ?? (hasRole('employee') ? '/app' : '/')
  }

  const required = [...to.matched].reverse().find((r) => r.meta.minRole)?.meta.minRole
  if (!required) return true

  if (isLoggedIn.value && !user.value) await fetchMe()
  if (!user.value) return { name: 'login', query: { next: to.fullPath } }
  if (hasRole(required)) return true
  return hasRole('employee') ? { name: 'app-dashboard' } : { name: 'home', query: { denied: '1' } }
})

const BASE_TITLE = typeof document !== 'undefined' ? document.title : ''
router.afterEach((to) => {
  if (typeof document === 'undefined') return
  document.title = to.meta.title ? `${to.meta.title} · Thimitech` : BASE_TITLE
})

export default router
