<template>
    <Error :error="error" />

    <div class="split-page">
      <div>
        <h1>Leaderboard</h1>

        <table v-if="leaderboard">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Team</th>
              <th>Solved Scenarios</th>
              <th>Members</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(team, index) in leaderboard" :key="team?.team_id" :class="{
              'highlight': team?.team_id === api.user?.team
              }">
              <td>{{ index + 1 }}</td>
              <td>{{ team?.name }}</td>
              <td>{{ api.solvedScenariosByPhase(team, api.currentPhase)  ?? 'Hidden' }}</td>
              <td>
                <ul class="members-list" v-if="team.members">
                  <li v-for="member in team.members">{{ member }}</li>
                </ul>
                <span v-else>Hidden</span>
              </td>
            </tr>
          </tbody>
        </table>
        <div class="loading" v-else>
          Loading...
        </div>
        <p class="leaderboard-info">
          Leaderboard updates may be delayed by up to 5 minutes after you solve a challenge, don't worry, your points are still being counted!
        </p>
      </div>
      <div>
        <h1>Scenarios</h1>

        <table>
          <thead>
            <tr>
              <th>Scenario</th>
              <th>Solves</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="scenario in api.scenarios" :key="scenario.scenario_id" :class="{
              'highlight': api.team?.solved_scenarios.includes(scenario.scenario_id)
            }">
              <td>{{ scenario.name }}</td>
              <td>{{ scenario.solves }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Markdown :value="scoresMarkdown"/>
  </template>
  
  <style scoped>
  table {
    width: 100%;
    border-collapse: collapse;
  }

  th, td {
    border: 1px solid var(--color-bg-dark);
    padding: 8px;
    text-align: left;
    word-wrap: break-word;
    word-break: break-word;
  }

  th {
    background-color: var(--color-bg-dark);
  }

  tr.highlight {
    background-color: #85dff689;
  }

  .members-list {
    list-style-type: none;
    padding: 0;
    margin: 0;
  }

  .split-page {
    display: flex;
    flex-direction: row;
    justify-content: space-between;
  }

  .split-page > div {
    flex: 1;
    margin-right: 1rem;
  }

  @media (max-width: 1200px) { /* Adjust the max-width as needed */
    .split-page {
      flex-direction: column;
    }
  }

  .leaderboard-info {
    margin-top: 1rem;
    font-size: 0.9rem;
    font-style: italic;
    text-align: center;
  }
  </style>
  
  <script setup lang="ts">
  import Error from '@/components/Error.vue';
  import Markdown from '@/components/Markdown.vue';
  import { useApiStore } from '../stores/api'
  import scoresMarkdown from '@/content/scores.md?raw'
  import { computed, ref } from 'vue'
  
  const api = useApiStore()
  const error = ref(null)

  api.getAllTeams().catch((err) => {
    error.value = err
  })

  api.fetchScenarios().catch((err) => {
    error.value = err
  })

  api.getLeaderboard().catch((err) => {
    error.value = err
  })

  const leaderboard = computed(() => {
    return api.teams && api.leaderboard && api.leaderboard.teams.map(team => api.teams[team] || { name: "Loading..." }) || []
  })
  </script>