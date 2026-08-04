import { Routes, Route, Navigate } from 'react-router-dom'

/**
 * App.tsx — Top-level router for Themis frontend.
 *
 * Routes:
 *   /                        → redirect to /portfolio
 *   /contracts               → Contract upload + list view
 *   /contracts/:contractId   → Contract viewer with inline clause flags
 *   /portfolio               → Portfolio risk heatmap
 *   /negotiate/:sessionId    → Negotiation simulation transcript viewer
 *   /alerts                  → Regulatory alerts panel
 *
 * TODO (Phase 4): Implement route components.
 * Each route maps to a page component in src/pages/ (to be created).
 */

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/portfolio" replace />} />
      {/* TODO (Phase 4): Replace placeholders with real page components */}
      <Route path="/portfolio"    element={<PlaceholderPage name="Portfolio Heatmap" />} />
      <Route path="/contracts"    element={<PlaceholderPage name="Contract List" />} />
      <Route path="/contracts/:contractId" element={<PlaceholderPage name="Contract Viewer" />} />
      <Route path="/negotiate/:sessionId"  element={<PlaceholderPage name="Negotiation Viewer" />} />
      <Route path="/alerts"       element={<PlaceholderPage name="Regulatory Alerts" />} />
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
