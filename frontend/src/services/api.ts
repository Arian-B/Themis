/**
 * services/api.ts — Typed API client layer for Themis frontend.
 *
 * All HTTP calls to the FastAPI backend go through this module.
 * Uses axios with a shared instance that:
 *   - Reads the JWT from Zustand auth store and adds Authorization header
 *   - Handles 401 responses by clearing auth state + redirecting to login
 *   - Adds request ID header for end-to-end tracing (matches Langfuse session)
 *
 * Type contracts mirror the backend Pydantic schemas.
 */

import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
})

// Request interceptor for JWT header
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('themis_jwt')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  config.headers['X-Request-ID'] = crypto.randomUUID()
  return config
})

// Response interceptor for 401 handling
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('themis_jwt')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export interface JurisdictionResult {
  country: string
  region: string | null
  confidence: number
  reasoning: string
}

export interface Clause {
  id: string
  title: string
  text: string
  order: number
  clause_type: string
}

export interface RiskFlag {
  clause_id: string
  concern: string
  risk_level: 'critical' | 'high' | 'medium' | 'low'
  citation_ids: string[]
  suggested_redline: string | null
  grounded: boolean
}

export interface VerificationResult {
  source_risk_flag_id: string
  claim: string
  source_text: string
  grounded: boolean
  citation_id: string
}

export interface ContractResults {
  jurisdiction: JurisdictionResult
  clauses: Clause[]
  risk_flags: RiskFlag[]
}

export interface ReviewQueueItem {
  clause_id: string
  concern: string
  risk_level: 'critical' | 'high' | 'medium' | 'low'
  grounded: boolean
}

export interface ReviewQueueResponse {
  queue: ReviewQueueItem[]
}

export interface ReviewSubmitRequest {
  flag_id: string
  decision: 'accepted' | 'rejected'
}

export interface ReviewSubmitResponse {
  status: string
  flag_id: string
  decision: string
}

export interface ContractStatus {
  status: 'processing' | 'awaiting_review' | 'complete'
}

export interface NegotiationStartRequest {
  contract_id: string
  clause_id: string
  client_position: string
}

export interface NegotiationStartResponse {
  session_id: string
}

export interface Redline {
  id: string
  turn: number
  speaker: 'proposer' | 'counterparty'
  proposed_text: string
  rationale: string
  diff_additions: string[]
  diff_deletions: string[]
  agreed: boolean
  impasse: boolean
}

export interface NegotiationTranscript {
  session_id: string
  contract_id: string
  clause_ids: string[]
  redlines: Redline[]
  final_status: 'agreed' | 'impasse' | 'in_progress'
  created_at: string
}

export const contractsApi = {
  upload: async (file: File): Promise<{ contract_id: string; status: string }> => {
    const formData = new FormData()
    formData.append('file', file)
    const response = await client.post('/contracts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  getStatus: async (contractId: string): Promise<ContractStatus> => {
    const response = await client.get(`/contracts/${contractId}/status`)
    return response.data
  },

  getResults: async (contractId: string): Promise<ContractResults> => {
    const response = await client.get(`/contracts/${contractId}/results`)
    return response.data
  },

  getReviewQueue: async (contractId: string): Promise<ReviewQueueResponse> => {
    const response = await client.get(`/contracts/${contractId}/review-queue`)
    return response.data
  },

  submitReview: async (contractId: string, payload: ReviewSubmitRequest): Promise<ReviewSubmitResponse> => {
    const response = await client.post(`/contracts/${contractId}/review`, payload)
    return response.data
  },

  startNegotiation: async (contractId: string, clauseId: string, clientPosition: string): Promise<NegotiationStartResponse> => {
    const response = await client.post('/negotiate', {
      contract_id: contractId,
      clause_id: clauseId,
      client_position: clientPosition,
    })
    return response.data
  },

  getNegotiationTranscript: async (sessionId: string): Promise<NegotiationTranscript> => {
    const response = await client.get(`/negotiate/${sessionId}`)
    return response.data
  },
}

export const portfolioApi = {
  getHeatmap: async (): Promise<unknown> => {
    const response = await client.get('/portfolio/heatmap')
    return response.data
  },

  getObligations: async (daysAhead: number): Promise<unknown> => {
    const response = await client.get('/portfolio/obligations', { params: { days_ahead: daysAhead } })
    return response.data
  },
}

export const alertsApi = {
  getAlerts: async (): Promise<unknown[]> => {
    const response = await client.get('/regulatory-alerts')
    return response.data
  },
}

export default client