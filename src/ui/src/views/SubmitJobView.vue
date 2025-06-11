<template>
  <div class="new-job">
    <h1>Submit a job</h1>
    <p>
      Submit a new job for execution. You can choose the model, defense, scenario, and prompt for your job.
    </p>

    <h2>Select a Scenario</h2>
    <label for="scenario">Scenario</label>

    <AccessibleSelect :items="api.scenarios" @update="setScenario($event as Scenario)" placeholder="Select a scenario">
      <template #selected="ctx">
        {{ ctx.item.name }}
        <span :class="{
          'tag': true,
          'primary': !api.team?.solved_scenarios?.includes(ctx.item.scenario_id) && ctx.item.solves > 0,
          'warning': !api.team?.solved_scenarios?.includes(ctx.item.scenario_id) && ctx.item.solves === 0,
          'success': api.team?.solved_scenarios?.includes(ctx.item.scenario_id) }">
            {{ ctx.item.solves }} solve{{ ctx.item.solves === 1 ? '' : 's' }}
        </span>
      </template>

      <template #item="ctx">
        {{ ctx.item.name }}
        <span :class="{
          'tag': true,
          'primary': !api.team?.solved_scenarios?.includes(ctx.item.scenario_id) && ctx.item.solves > 0,
          'warning': !api.team?.solved_scenarios?.includes(ctx.item.scenario_id) && ctx.item.solves === 0,
          'success': api.team?.solved_scenarios?.includes(ctx.item.scenario_id) }">
            {{ ctx.item.solves }} solve{{ ctx.item.solves === 1 ? '' : 's' }}
        </span>
      </template>
    </AccessibleSelect>

    <div v-if="scenario">
      <h3>
        Scenario Details
        
        <span class="tag primary">id: {{ scenario.scenario_id }}</span>
        <span class="tag success" v-if="scenario && isSolved">Solved</span>
        <span class="tag warning" v-if="scenario && !isSolved">Unsolved</span>

        <span class="tag" v-for="(value, key) in scenario?.metadata || {}" :key="key"><strong>{{ key }}</strong>: {{ value }}</span>
      </h3>
      <p>
        {{ scenario?.description }}
      </p>
      <p>
        <strong>Objectives:</strong> <span v-for="objective in scenario?.objectives || []" :key="objective" class="tag primary">{{ objective }}</span>
      </p>
      <p>
        <strong>Solved by</strong> {{ scenario.solves - (isSolved ? 1 : 0) }} other team{{ (scenario.solves - (isSolved ? 1 : 0)) === 1 ? '' : 's' }}.
      </p>
    </div>

    <h2>Write your E-mail</h2>
    <p>
      Write the email you plan to send to the target, including the details of the subject and body. This
      email may be evaluated as part of the scenario depending on the manner in which the scenario is configured. Your goal
      is to craft an email that will achieve the scenario objectives (usually executing an attack and evading detection).
    </p>
    
    <label for="emailSubject">Subject</label>
    <input type="text" id="emailSubject" v-model="emailSubject" placeholder="Enter the subject of your email..." />

    <label for="emailBody">Body</label>
    <textarea id="emailBody" v-model="emailBody" placeholder="Write the content of your email here" rows="10"></textarea>

    <button @click="submitJob()" :disabled="!sendEnabled">Create Job</button>

    <Notification v-if="isSolved" kind="warning">
      You have already solved this scenario, you will not receive any additional points for solving it a second time,
      however you are welcome to submit additional attempts to test alternate strategies.
    </Notification>

    <Error :error="error" />
  </div>
</template>

<script setup lang="ts">
  import { useApiStore } from '../stores/api'
  import { ref, computed } from 'vue'
  import { useRouter } from 'vue-router'
  import Error from '../components/Error.vue'
  import type { JobSubmission, Scenario } from '../models/models'
  import Notification from '@/components/Notification.vue'
  import AccessibleSelect from '@/components/AccessibleSelect.vue'

  const api = useApiStore()
  const router = useRouter()

  const error = ref<Record<string, string>|undefined>(undefined)
  const sending = ref(false)

  const scenario = ref<Scenario|null>(null)
  const emailSubject = ref('')
  const emailBody = ref('')

  const sendEnabled = computed(() => {
    return !sending.value && scenario.value && emailSubject.value && emailBody.value
  })

  const isSolved = computed(() => {
    return scenario.value && api.team && (api.team.solved_scenarios || []).includes(scenario.value.scenario_id)
  })

  const scenarioItems = computed(() => {
    return (api.scenarios || []).map(scenario => ({
      value: scenario.scenario_id,
      text: `${scenario.name} (${scenario.solves} solve${scenario.solves === 1 ? '' : 's'})`
    }))
  })

  function setScenario(s: Scenario) {
    scenario.value = s
  }

  function submitJob() {
    if (!sendEnabled.value) {
      return
    }

    sending.value = true
    api.createJob({
      scenario: scenario.value!.scenario_id,
      subject: emailSubject.value,
      body: emailBody.value,
    }).then((job) => {
      router.push({ name: 'job', params: { jobId: job.job_id } })
    }).catch((err) => {
      sending.value = false
      error.value = err
    })
  }

  
</script>