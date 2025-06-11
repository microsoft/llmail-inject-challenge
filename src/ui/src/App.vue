<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import Menu from './components/Menu.vue'

import { useApiStore } from './stores/api'

const api = useApiStore()
api.fetchScenarios()
api.fetchUserInfo().then(() => api.fetchTeamInfo())

const announcementMessage = `Phase 2 has ended! Congratulations to the three top teams: "TH3L053R5", "299", "RainaResearch"!! Please get in touch with us at: llmailinject@microsoft.com`
</script>

<template>
  <header>
    <div class="logo">
      Adaptive Prompt Injection Challenge
    </div>
    <Menu />
  </header>

  <div class="announcement-banner">
    <span class="emoji">📢</span>
    <span class="message">{{ announcementMessage }}</span>
  </div>

  <div class="content">
    <RouterView />
  </div>
</template>

<style scoped>
header {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  background-color: var(--color-bg-dark);
  padding: 0 1rem;
}

.logo {
  font-size: 1.5rem;
  font-weight: 100;
}

.logo img {
  height: 32px;
  aspect-ratio: 1;
  vertical-align: middle;
  padding: 1rem;
}

.announcement-banner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 15px 25px;
  background: linear-gradient(90deg, #e3f2fd, #bbdefb); 
  color: #0d47a1; 
  border: 1px solid #90caf9;  
  border-radius: 12px;  
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
  font-size: 16px;
  font-weight: bold;
  margin: 1rem 0;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.announcement-banner:hover {
  transform: translateY(-2px);  
  box-shadow: 0 6px 10px rgba(0, 0, 0, 0.15);  
}

.emoji {
  font-size: 24px;  
  margin-right: 15px;
  animation: bounce 2s infinite;  
}

.message {
  font-family: Arial, sans-serif;
}

@keyframes bounce {
  0%, 20%, 50%, 80%, 100% {
    transform: translateY(0);
  }
  40% {
    transform: translateY(-5px);
  }
  60% {
    transform: translateY(-3px);
  }
}

.content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 1em 0;
}
</style>
