export interface User {
    login: string
    team?: string
    role: "competitor"|"admin"
    api_key: string
}

export interface Team {
    team_id: string
    name: string
    members: string[]
    score: number
    solved_scenarios: string[]
}

export interface Job extends JobSubmission {
    team_id: string
    job_id: string
    output?: string
    objectives?: Record<string, boolean>,
    scheduled_time: string
    started_time?: string
    completed_time?: string
}

export interface JobSubmission {
    scenario: string
    subject: string
    body: string
}

export interface Scenario {
    scenario_id: string
    phase: number
    name: string
    description: string
    metadata: Record<string, string>
    objectives: string[]
    solves: number
}

export interface Leaderboard {
    teams: string[]
    last_updated: string
}