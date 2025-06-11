<script setup lang="ts">
import { useApiStore } from '../stores/api'

const apiKey = useApiStore()
</script>

<template>
  <nav>
    <RouterLink to="/">Home</RouterLink>
    <RouterLink to="/leaderboard">Leaderboard</RouterLink>
    <RouterLink to="/scenarios">Scenarios</RouterLink>
    <RouterLink to="/rules">Rules</RouterLink>
    <RouterLink v-if="apiKey.team" to="/jobs">Jobs</RouterLink>
    <RouterLink v-if="apiKey.user" to="/api-client">API</RouterLink>
    <a class="github-tagged" v-if="!apiKey.user" href="/api/auth/login">Login or Register</a>
    <RouterLink class="github-tagged" v-if="apiKey.user" to="/me">
      {{ apiKey.user?.login || 'Account' }}
    </RouterLink>
  </nav>
</template>

<style scoped>
nav {
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    background-color: var(--color-bg-dark);
}

nav a {
    padding: 1.5em 1em;
    text-decoration: none;
    color: var(--color-text);
    border-bottom: 3px solid transparent;
    transition: border-color 0.3s ease-in-out;
}

nav a:hover {
    border-color: var(--color-primary-light);
}

nav a.router-link-active {
    border-color: var(--color-primary);
}
</style>
