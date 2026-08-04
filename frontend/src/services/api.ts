/**
 * services/api.ts — Typed API client layer for Themis frontend.
 *
 * All HTTP calls to the FastAPI backend go through this module.
 * Uses axios with a shared instance that:
 *   - Reads the JWT from Zustand auth store and adds Authorization header
 *   - Handles 401 responses by clearing auth state + redirecting to login
 *   - Adds request ID header for end-to-end tracing (matches Langfuse session)
 *
 * Type contracts: mirror the PydanticAI schemas from the backend.
 * In Phase 4, generate these types automatically from the FastAPI OpenAPI schema
 * using openapi-typescript-codegen.
 *
 * TODO (Phase 4): Implement all functions below.
 * TODO (Phase 4): Generate TypeScript types from /openapi.json using:
 *   npx openapi-typescript http://localhost:8000/openapi.json -o src/services/api.types.ts
 */

import axios from 'axios'

const client = axios.create({
  baseURL: '/api/v1',
  timeout: 30_000,
})

// TODO (Phase 4): Add request interceptor for JWT header
// TODO (Phase 4): Add response interceptor for 401 handling

export const contractsApi = {
  /** POST /contracts/analyze — upload PDF, returns {session_id, contract_id} */
  analyze: async (_file: File): Promise<{ session_id: string; contract_id: string }> => {
    throw new Error('Phase 4: contractsApi.analyze() not implemented')
  },

  /** GET /contracts/:id — returns ExtractedContract + VerifiedRiskReport */
  getContract: async (_contractId: string): Promise<unknown> => {
    throw new Error('Phase 4: contractsApi.getContract() not implemented')
  },
}

export const portfolioApi = {
  /** GET /portfolio/heatmap — returns 2D risk grid */
  getHeatmap: async (): Promise<unknown> => {
    throw new Error('Phase 4: portfolioApi.getHeatmap() not implemented')
  },

  /** GET /portfolio/obligations?days_ahead=30 */
  getObligations: async (_daysAhead: number): Promise<unknown> => {
    throw new Error('Phase 4: portfolioApi.getObligations() not implemented')
  },
}

export const negotiateApi = {
  /** POST /negotiate — start simulation */
  start: async (_contractId: string, _clauseIds: string[]): Promise<{ session_id: string }> => {
    throw new Error('Phase 4: negotiateApi.start() not implemented')
  },

  /** GET /negotiate/:sessionId — get completed transcript */
  getTranscript: async (_sessionId: string): Promise<unknown> => {
    throw new Error('Phase 4: negotiateApi.getTranscript() not implemented')
  },
}

export const alertsApi = {
  /** GET /regulatory-alerts */
  getAlerts: async (): Promise<unknown[]> => {
    throw new Error('Phase 4: alertsApi.getAlerts() not implemented')
  },
}

export default client
