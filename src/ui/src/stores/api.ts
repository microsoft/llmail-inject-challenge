import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import type { Job, JobSubmission, Leaderboard, Scenario, Team, User } from '@/models/models'

export const useApiStore = defineStore('api', {
    state() {
        return {
            user: null as User | null,
            team: null as Team | null,
            teams: {} as { [teamId: string]: Team },
            leaderboard: null as Leaderboard | null,
            jobs: {} as { [jobId: string]: Job },
            scenarios: [] as Scenario[],
            currentPhase: 2
        }
    },
    getters: {
        configured: (state) => !!state.user,
        solvedScenariosByPhase: (state) => (team: Team, phase: number) => {
            if (!team?.solved_scenarios?.length) {
              return 0
            }
            return team.solved_scenarios.filter((scenarioId) => {
              const scenario = state.scenarios.find(s => s.scenario_id === scenarioId)
              return scenario && scenario.phase === phase
            }).length
          },
    },
    actions: {
        async registerNewTeam(name: string) {
            const team = await this.callApi<Team>({
                path: '/api/teams',
                method: 'POST',
                body: { name },
                auth: false
            })

            this.team = team
            this.user!.team = team.team_id
        },

        async fetchUserInfo() {
            this.user = await this.callApi<User>({
                method: 'GET',
                path: '/api/auth/me',
                auth: true,
            })
        },

        async rotateApiKey() {
            this.user = await this.callApi<User>({
                method: 'POST',
                path: '/api/auth/rotate-key',
                auth: true,
            })
        },
    
        async fetchTeamInfo() {
            this.team = await this.callApi<Team>({
                method: 'GET',
                path: `/api/teams/mine`,
                auth: true,
            })
        },

        async fetchScenarios() {
            this.scenarios = await this.callApi<Scenario[]>({
                method: 'GET',
                path: '/api/scenarios',
                auth: false,
            })
        },

        async getAllTeams() {
            const teams = await this.callApi<Team[]>({
                method: 'GET',
                path: '/api/teams',
                auth: false,
            })

            this.teams = teams.reduce((acc, team) => {
                acc[team.team_id] = team
                return acc
            }, {} as { [teamId: string]: Team })
        },

        async getLeaderboard() {
            this.leaderboard = await this.callApi<Leaderboard>({
                method: 'GET',
                path: '/api/leaderboard',
                auth: false,
            })
        },

        async getAllJobs() {
            const jobs = await this.callApi<Job[]>({
                method: 'GET',
                path: `/api/teams/mine/jobs`,
                auth: true,
            })

            this.jobs = jobs.reduce((acc, job) => {
                acc[job.job_id] = job
                return acc
            }, {} as { [jobId: string]: Job })
        },

        async getJob(jobId: string) {
            this.jobs[jobId] = await this.callApi<Job>({
                method: 'GET',
                path: `/api/teams/mine/jobs/${jobId}`,
                auth: true,
            })
        },

        async createJob(job: JobSubmission) {
            const newJob = await this.callApi<Job>({
                method: 'POST',
                path: `/api/teams/mine/jobs`,
                auth: true,
                body: job,
            })

            this.jobs[newJob.job_id] = newJob

            return newJob
        },

        async deleteTeam() {
            await this.callApi<void>({
                method: 'DELETE',
                path: `/api/teams/mine`,
                auth: true,
            })

            this.team = null
            if (this.user) {
                this.user.team = undefined
            }
        },

        async updateTeam({ members }: { members: string[] }) {
            this.team = await this.callApi<Team>({
                method: 'PATCH',
                path: `/api/teams/mine`,
                auth: true,
                body: { members: members },
            })
        },

        async callApi<T>({
            path,
            method = 'GET',
            auth = true,
    
            body = null,
        }: {
            path: string,
            method: string,
            auth: boolean,
            body?: unknown,
        }): Promise<T> {
            const url = `${path}`
            const headers: Record<string, string> = {}
    
            if (body) {
                headers['Content-Type'] = 'application/json'
            }
    
            const response = await fetch(url, {
                method,
                headers,
                body: body ? JSON.stringify(body) : null,
            })
    
            if (!response.ok) {
                const error: {
                    message: string,
                    advice: string,
                    trace_id?: string,
                } = await response.json()
                throw new ApiError(error.message, error.advice, error.trace_id)
            }

            if (response.headers.get('Content-Type')?.startsWith('application/json')) {
                return await response.json()
            } else {
                return null as T
            }
        }
    }
})

class ApiError extends Error {
    constructor(message: string, public advice: string, public trace_id?: string) {
        super(message)
    }
}