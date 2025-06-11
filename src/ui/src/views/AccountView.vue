<template>
  <div class="account">
    <div class="notification success" v-if="api.configured && api.user">
      <p>
        You are signed in as <strong class="github-tagged inverted">{{ api.user.login }}</strong>.
      </p>
    </div>

    <h2>Your Team</h2>
    <div v-if="api.team">
      <p>
        You are a member of the team <strong>{{ api.team.name }}</strong>.
      </p>
      <p>
        Your team members are:
      </p>
      <ul class="members-list">
        <li v-for="member in api.team.members" :key="member">
          <strong class="github-tagged">
            {{ member }}
          </strong>
          <span v-if="member === api.user?.login"> (you)</span>
          <a class="tag error remove-button" v-else @click="removeTeamMember(member)">Remove</a>
        </li>
      </ul>

      <button v-if="api.team?.members?.length === 1" class="error" @click="deleteTeam()">Delete Team</button>
      
      <h3>Add a Team Member</h3>
      <p>
        You can add a new person to your team by entering their GitHub username here.
        They will need to have registered an account on this site before you can add them
        (and they must not be a member of another team).
      </p>

      <label for="newTeamMemberName">GitHub Username</label>
      <input type="text" id="newTeamMemberName" v-model="newTeamMemberName" placeholder="github-username" />

      <Error :error="error" />

      <button :disabled="!addMemberEnabled" @click="addTeamMember()">Add Team Member</button>
    </div>
    <div v-else>
      <p>
        You are not a member of a team. To play, <strong>you must</strong> either create a new team or join an existing team.
        A member of a team will be able to add you to their team using your GitHub username.
      </p>

      <label for="teamName">Team Name</label>
      <input type="text" id="teamName" v-model="teamName" placeholder="Enter a team name..." />
      
      <Error :error="error" />

      <button :disabled="!registerTeamEnabled" @click="registerTeam()">Create Team</button>
    </div>

    <h2>Your Account</h2>
    <h3>API Key</h3>
    <input type="text" readonly :value="api.user?.api_key" />
    <p>
      You can rotate your API key to invalidate any currently active sessions or if you
      suspect that your API key has been compromised. We recommend you do not share your
      API key with anyone else.
    </p>
    <p>
      For more information on using your API key, see the <a href="/api-client">API documentation</a>.
    </p>

    <button class="warning" @click="rotateApiKey()">Rotate API Key</button>

    <h3>Account Management</h3>
    <p>
      You can logout of your account at any time. Logging out will clear your active session,
      but will not invalidate your API key.
    </p>

    <button class="error" @click="logout()">Logout</button>

  </div>
</template>

<style scoped>
.account {
  margin: 0 auto;
  max-width: 640px;
}

.members-list {
  list-style: none;
  padding: 0 0.5rem;
}

.members-list li {
  margin: 0.5em 0;
}

.remove-button {
  cursor: pointer;
}

input[readonly] {
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useApiStore } from '../stores/api'
import { useRouter } from 'vue-router'
import Error from '../components/Error.vue'

const api = useApiStore()
const router = useRouter()

const sending = ref(false)
const teamName = ref('')
const newTeamMemberName = ref('')
const error = ref<Record<string, string>|undefined>(undefined)

const addMemberEnabled = computed(() => {
  return !sending.value && newTeamMemberName.value.trim()
})

function addTeamMember() {
  if (!addMemberEnabled.value) {
    return
  }

  sending.value = true
  api.updateTeam({
    members: [...api.team!.members, newTeamMemberName.value]
  }).then(() => {
    sending.value = false
    newTeamMemberName.value = ''
  }).catch((err) => {
    sending.value = false
    error.value = err
  })
}

const registerTeamEnabled = computed(() => {
  return !api.team && !sending.value && teamName.value.trim()
})

function registerTeam() {
  if (!registerTeamEnabled.value) {
    return
  }

  sending.value = true
  api.registerNewTeam(teamName.value).then(() => {
    sending.value = false
  }).catch((err) => {
    sending.value = false
    error.value = err
  })
}

function deleteTeam() {
  if (!api.team) {
    return
  }

  sending.value = true
  api.deleteTeam().then(() => {
    sending.value = false
  }).catch((err) => {
    sending.value = false
    error.value = err
  })
}

function removeTeamMember(member: string) {
  api.updateTeam({
    members: api.team!.members.filter((m) => m !== member)
  }).then(() => {
    sending.value = false
  }).catch((err) => {
    sending.value = false
    error.value = err
  })
}

function logout() {
  window.location.href = '/api/auth/logout'
}

function rotateApiKey() {
  api.rotateApiKey().then(() => {
    sending.value = false
  }).catch((err) => {
    sending.value = false
    error.value = err
  })
}
</script>