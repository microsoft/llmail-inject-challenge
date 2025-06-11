<template>
    <h1>
      <div class="header">
          Job Details

        <span class="tag success" v-if="job?.completed_time && isSolved">Solved</span>
        <span class="tag warning" v-if="job?.completed_time && !isSolved">Unsolved</span>
        <span class="tag primary" v-if="job && !job.completed_time">Running</span>
        <span class="tag primary" v-if="!job">Loading...</span>
      </div>
    </h1>
    
    <h2>Status</h2>
    <Error :error="error" />

    <Notification v-if="!error && !job?.completed_time" kind="primary">
      This job is currently scheduled for execution, more details will be provided once it completes.
    </Notification>

    <div v-if="scenario">
      <h2 class="header">
        Scenario
        
        <span class="tag primary">id: {{ scenario.scenario_id }}</span>
        
        <span>
          <span class="tag" v-for="(value, key) in scenario?.metadata || {}" :key="key"><strong>{{ key }}</strong>: {{ value }}</span>
        </span>
      </h2>
      <p>
        {{ scenario?.description }}
      </p>
    </div>

    <h2>
      <div class="header">
        Input
      </div>
    </h2>
    <p>
      <strong>Subject</strong> {{ job?.subject }}
      
    </p>

    <p>
      {{ job?.body }}
    </p>

    <div>
      <h2>
        <div class="header">
          Result

          <span v-if="job?.completed_time && isSolved" class="tag success">Solved</span>
          <span v-if="job?.completed_time && !isSolved" class="tag warning">Unsolved</span>
          <span v-if="!job.completed_time" class="tag primary">Waiting for results {{ ago(job?.scheduled_time) }}</span>
        </div>
      </h2>

      <h3>Objectives</h3>
      <ul>
        <li v-for="(achieved, objective) in job?.objectives">
          {{ objective }}: <span :class="{
          'tag': true,
          'success': achieved,
          'warning': !achieved
        }">{{ achieved ? 'achieved' : 'not achieved' }}</span>
        </li>
      </ul>
    </div>


  </template>
  
  <style scoped>
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .header button {
    width: auto;
  }

  .jobs {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 16px;
  }

  .job {
    border: 1px solid var(--color-bg-dark);
    padding: 0.5rem 1rem;
    border-radius: 4px;
    box-shadow: 5px 5px 20px var(--color-shadow);

    border-left: 8px solid var(--color-primary);
  }

  .job.completed {
    border-left: 8px solid var(--color-success);
  }

  .job h2 {
    margin-top: 0;
  }

  .tags {
    margin: 0;
  }

  .output {
    font-style: italic;
    margin: 1rem 0.5rem;
  }
  </style>
  
  <script setup lang="ts">
  import { useApiStore } from '../stores/api'
  import { useRouter } from 'vue-router'
  import { ref, computed, onMounted, onBeforeUnmount, onUnmounted } from 'vue'
  import Error from '../components/Error.vue'
  import Notification from '@/components/Notification.vue'
  import type { Job } from '../models/models'
  import { DateTime, Duration } from 'luxon'

  let refreshHandle: number|undefined
  
  const api = useApiStore()
  const router = useRouter()
  const error = ref<Record<string, string>|undefined>(undefined)

  const props = defineProps<{
    jobId: string
  }>()

  const job = computed(() => {
    return api.jobs[props.jobId]
  })

  const scenario = computed(() => {
    const scenarioId = job.value?.scenario || ''
    if (!scenarioId) {
      return null
    }

    return api.scenarios.find((s) => s.scenario_id === scenarioId)
  })

  const isSolved = computed(() => {
    return scenario.value && job.value && job.value.objectives && scenario.value.objectives.every((objective) => job.value.objectives![objective])
  })

  function ago(time: string): string {
    return DateTime.fromISO(time).toRelative() || time
  }

  onMounted(() => {
    const onJobsUpdated = () => {
      if (!job.value?.completed_time) {
        refreshHandle = setInterval(() => {
          api.getAllJobs().then(() => {
            if (job.value?.completed_time) {
              clearInterval(refreshHandle)
            }
          }).catch((err) => {
            error.value = err
          })
        }, 10000)
      }
    }


    if (!api.jobs[props.jobId]) {
      api.getAllJobs().then(onJobsUpdated).catch((err) => {
        error.value = err
      })
    } else if (!job.value?.completed_time) {
      onJobsUpdated()
    }

    api.fetchScenarios().catch((err) => {
      error.value = err
    })
  })

  onUnmounted(() => {
    if (refreshHandle) {
      clearInterval(refreshHandle)
    }
  })
  </script>