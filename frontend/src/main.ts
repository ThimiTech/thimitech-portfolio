import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './assets/Tailwind.css'

// A single-page app renders after the browser has already restored the previous
// scroll offset, which lands visitors halfway down the page on reload. Take control:
// the router decides where each navigation starts.
if ('scrollRestoration' in history) history.scrollRestoration = 'manual'

createApp(App).use(router).mount('#app')

// Belt and braces for the first paint. Some browsers restore a scroll offset after
// the app has mounted; when the address bar still carries a hash from an earlier
// visit, make sure the visitor still starts on the landing page.
if (window.location.hash) {
  requestAnimationFrame(() => window.scrollTo(0, 0))
}
