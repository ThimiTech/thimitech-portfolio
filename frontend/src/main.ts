import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/Tailwind.css'

createApp(App).use(router).mount('#app')
