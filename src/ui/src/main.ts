import './assets/main.css'

import { createApp } from 'vue'
import { createPinia } from 'pinia'

import 'highlight.js/styles/stackoverflow-dark.min.css'
import hljs from 'highlight.js/lib/core';

import hljsPython from 'highlight.js/lib/languages/python'
hljs.registerLanguage('python', hljsPython)

import hljsJson from 'highlight.js/lib/languages/json'
hljs.registerLanguage('json', hljsJson)

import hljsBash from 'highlight.js/lib/languages/bash'
hljs.registerLanguage('bash', hljsBash)

import hljsHttp from 'highlight.js/lib/languages/http'
hljs.registerLanguage('http', hljsHttp)

import hljsVuePlugin from '@highlightjs/vue-plugin'

const pinia = createPinia()

import App from './App.vue'
import router from './router'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(hljsVuePlugin)

app.mount('#app')
