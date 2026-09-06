import { Routes, Route, Navigate } from 'react-router-dom'
import { ContractUploadPage } from './pages/ContractUploadPage'
import { ContractResultsPage } from './pages/ContractResultsPage'
import { ReviewQueuePage } from './pages/ReviewQueuePage'
import { NegotiationPage } from './pages/NegotiationPage'

/**
 * App.tsx — Top-level router for Themis frontend.
 *
 * Routes:
 *   /                        → redirect to /contracts (upload)
 *   /contracts               → Contract upload view
 *   /contracts/:contractId   → Contract results viewer
 *   /contracts/:contractId/review → Review queue
 *   /negotiate/:sessionId    → Negotiation simulation transcript viewer
 *   /portfolio               → Portfolio risk heatmap (placeholder)
 *   /alerts                  → Regulatory alerts panel (placeholder)
 */

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/contracts" replace />} />
      <Route path="/contracts" element={<ContractUploadPage />} />
      <Route path="/contracts/:contractId" element={<ContractResultsPage />} />
      <Route path="/contracts/:contractId/review" element={<ReviewQueuePage />} />
      <Route path="/negotiate/:sessionId" element={<NegotiationPage />} />
      <Route path="/portfolio" element={<PlaceholderPage name="Portfolio Heatmap" />} />
      <Route path="/alerts" element={<PlaceholderPage name="Regulatory Alerts" />} />
    </Routes>
  )
}

/** Temporary placeholder for unimplemented pages. Remove in Phase 4. */
function PlaceholderPage({ name }: { name: string }) {
  return (
    <div style={{ padding: '2rem', fontFamily: 'sans-serif', color: '#e2e8f0', background: '#0f172a', minHeight: '100vh' }}>
      <h1 style={{ color: '#a78bfa' }}>Themis</h1>
      <p style={{ color: '#64748b' }}>{name} — implement in Phase 4</p>
    </div>
  )
}
