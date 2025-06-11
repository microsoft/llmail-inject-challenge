<template>
    <div class="header">
      <h1>Jobs</h1>

      <button @click="router.push({ name: 'createJob' })">+ New Job</button>
    </div>

    <Error :error="error" />

    <div class="jobs" role="list">
      <div class="job" role="listitem" tabindex="0" v-for="job in jobs" :key="job.job_id" :class="{
        completed: !!job.completed_time
      }" @click="viewJobDetails(job)" @keydown.enter="viewJobDetails(job)"
      :aria-label="`Job ${jobName(job)}`"
      >
        <h2>
          {{ jobName(job) }}

        </h2>

        <p class="tags">
          <span v-if="!job.completed_time" class="tag primary">Running</span>
          <span v-for="(achieved, objective) in job.objectives" :class="{
            'tag': true,
            'success': achieved,
            'warning': !achieved
          }">
            {{ objective }}
          </span>
        </p>

        <p>
          {{ job.body }}
        </p>
      </div>
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
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
  }

  .job {
    flex: 1 1 300px;
    max-width: 100%;
    box-sizing: border-box;
    border: 1px solid var(--color-bg-dark);
    padding: 0.5rem 1rem;
    border-radius: 4px;
    box-shadow: 5px 5px 20px var(--color-shadow);

    border-left: 8px solid var(--color-primary);
    cursor: pointer;
  }

  .job:hover,
  .job:focus {
    border-left: 8px solid var(--color-primary-light);
  }

  .job.completed {
    border-left: 8px solid var(--color-success);
  }

  .job.completed:hover,
  .job.focus:hover {
    border-left: 8px solid var(--color-success-light);
  }

  .job h2 {
    margin-top: 0;
  }

  .tags {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  </style>
  
  <script setup lang="ts">
  import { useApiStore } from '../stores/api'
  import { useRouter } from 'vue-router'
  import { ref, computed } from 'vue'
  import Error from '../components/Error.vue'
  import type { Job } from '../models/models'
  
  const api = useApiStore()
  const router = useRouter()
  const error = ref<Record<string, string>|undefined>(undefined)

  api.getAllJobs().catch((err) => {
    error.value = err
  })

  const jobs = computed(() => {
    return Object.values(api.jobs).sort((a, b) => -a.scheduled_time.localeCompare(b.scheduled_time))
  })

  function jobName(job: Job): string {
    return `${job.subject} (${job.scenario})`
  }

  function viewJobDetails(job: Job) {
    router.push({ name: 'job', params: { jobId: job.job_id } })
  }
  </script>