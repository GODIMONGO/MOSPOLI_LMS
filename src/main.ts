import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '@fontsource/roboto/400.css'
import '@fontsource/roboto/500.css'
import '@fontsource/roboto/700.css'

const app = createApp(App)
app.use(router)
app.mount('#app')