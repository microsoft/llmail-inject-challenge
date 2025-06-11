import { createRouter, createWebHistory } from 'vue-router'
import HomeView from '../views/HomeView.vue'
import LoginView from '../views/AccountView.vue'
import LeaderboardView from '../views/LeaderboardView.vue'
import JobsView from '@/views/JobsView.vue'
import JobView from '@/views/JobView.vue'
import SubmitJobView from '@/views/SubmitJobView.vue'
import ClientView from '@/views/ClientView.vue'
import RulesView from '@/views/RulesView.vue' 
import ScenariosView from '@/views/ScenariosView.vue' 


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView
    },
    {
      path: '/leaderboard',
      name: 'leaderboard',
      component: LeaderboardView
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: JobsView
    },
    {
      path: '/jobs/new',
      name: 'createJob',
      component: SubmitJobView
    },
    {
      path: '/jobs/:jobId',
      name: 'job',
      component: JobView,
      props: true
    },
    {
      path: '/login',
      name: 'login',
      component: LoginView
    },
    {
      path: '/me',
      name: 'account',
      component: LoginView
    },
    {
      path: '/api-client',
      name: 'client',
      component: ClientView
    },
    {
      path: '/scenarios',
      name: 'scenarios',
      component: ScenariosView
    },
    {
      path: '/rules',
      name: 'rules',
      component: RulesView
    },
  ]
})

export default router
