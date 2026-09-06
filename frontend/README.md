# Themis Frontend

React + Vite + TypeScript frontend for Themis legal intelligence platform.

## Prerequisites

- **Node.js 20+** (tested on 20.x)
- **npm 10+** (bundled with Node)
- **Backend API running on `http://localhost:8000`** (see root README)

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Opens at `http://localhost:5173` with API proxy to `http://localhost:8000`.

## Environment Variables

None required for development. The Vite config proxies `/api` → `http://localhost:8000` automatically.

## Verified Test Flow

1. **Upload Contract** — `http://localhost:5173/contracts`
   - Drag-and-drop or click to select `data/raw/MSA_SaaS.txt` (or any contract text)
   - Click "Upload & Analyze" → redirects to `/contracts/:contractId`

2. **Poll Status** — Results page polls `GET /contracts/{id}/status` every 3s
   - Shows spinner until status = `awaiting_review` or `complete`

3. **View Results** — `GET /contracts/{id}/results`
   - Jurisdiction card (country, confidence, reasoning)
   - Clauses list (title, type, text)
   - Risk flags table with badges:
     - Risk level: critical=red, high=orange, medium=yellow, low=blue
     - Grounded: ✅ green check / ❌ red X
     - Citations linked to retrieved sources

4. **Review Queue** — Click "Review Queue" button or navigate to `/contracts/{id}/review`
   - `GET /contracts/{id}/review-queue` returns only high-risk/ungrounded flags
   - Each row: clause_id, concern, risk_level badge, grounded badge
   - Accept/Reject buttons → confirmation modal → `POST /contracts/{id}/review`
   - On success: item removed from queue immediately, toast notification

5. **Negotiation** — From results page, navigate to `/negotiate` (or click accepted flag)
   - Select single clause (radio) + client position textarea
   - `POST /negotiate` → returns `session_id` → redirects to `/negotiate/{session_id}`
   - Transcript renders all turns with:
     - Speaker label (PROPOSER blue / COUNTERPARTY purple)
     - Turn number badge
     - Proposed text + rationale
   - Final status badge: AGREED (green) / IMPASSE (red) / MAX TURNS REACHED (yellow)

## Component Library (src/components/common)

| Component | Purpose |
|-----------|---------|
| `Button` | Primary/secondary/ghost/danger variants, loading state |
| `Badge` | risk-level variants (critical/high/medium/low), success/warning/danger |
| `Card` / `CardHeader` / `CardTitle` / `CardDescription` / `CardContent` | Consistent card layout |
| `Input` / `Textarea` | Form inputs with label, error, helper text |
| `Spinner` / `Loader` | Loading states |
| `Modal` | Confirmation dialogs, portable via portal |
| `ErrorBoundary` | Graceful error fallback |
| `ToastContainer` | Bottom-right notifications (success/error/info/loading) |

## State Management (src/store)

- `useAuthStore` — JWT in localStorage (dev token injected)
- `useContractStore` — Current contract ID, upload status, results, review queue
- `useNegotiationStore` — Active session ID, transcript, connection status

## API Client (src/services/api.ts)

Axios instance with:
- JWT from `localStorage.themis_jwt` → `Authorization` header
- 401 handling → clears auth, redirects to `/login`
- Request ID header for tracing
- All typed endpoints matching backend Pydantic schemas

## Type Safety

```bash
npm run type-check  # tsc --noEmit
```

All pages, hooks, and API calls fully typed.

## Styling

- CSS variables in `src/index.css` (design tokens)
- Utility classes for risk levels, glass cards, animations
- Dark slate theme (Inter font, JetBrains Mono for code)
- Consistent spacing, focus states, scrollbar styling

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server (HMR) |
| `npm run build` | Production build to `dist/` |
| `npm run preview` | Preview production build |
| `npm run type-check` | TypeScript check |
| `npm run lint` | ESLint (config needs migration to flat) |

## Architecture Notes

- **No WebSocket** — Negotiation runs synchronously in backend, returns full transcript
- **Test JWT** — Auto-injected in dev: `test-token-tenant-...` (works with backend test backdoor)
- **Proxy** — `/api/*` → `http://localhost:8000` via Vite config
- **No separate login page** — Dev token auto-set, real auth would replace this