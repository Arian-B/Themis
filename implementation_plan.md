# Day 7 Implementation Plan: FastAPI Backend & n8n Automation

## Objective
Build a production-grade FastAPI application that wraps the Themis LangGraph pipeline, protected by Supabase JWT authentication. Integrate an n8n webhook automation for high-risk flags, update docker-compose, and test cross-tenant isolation and the full HTTP lifecycle.

## Proposed Changes

### 1. Backend API (`api/`)
#### [MODIFY] [api/dependencies.py](file:///d:/Coding/themis/api/dependencies.py)
- Implement `get_current_tenant` to extract and validate the Supabase JWT from the Authorization header and return the `tenant_id`. 

#### [MODIFY] [api/main.py](file:///d:/Coding/themis/api/main.py)
- Include the `contracts` router.
- Define basic startup/liveness handlers.

#### [MODIFY] [api/routers/contracts.py](file:///d:/Coding/themis/api/routers/contracts.py)
- **POST `/upload`**: Accept text/PDF, save a dummy record to Supabase `contracts` table (with `contract_id`), run `graph.ainvoke` asynchronously using FastAPI's `BackgroundTasks`, and immediately return `contract_id` and `status="processing"`.
- **GET `/{contract_id}/status`**: Query the checkpointer using `contract_id` (used as `thread_id`) to return the current graph state (e.g. `awaiting_review`, `processing`, `complete`).
- **GET `/{contract_id}/results`**: Query the checkpointer state and return `jurisdiction_result`, `extraction_result`, `risk_analysis_result`, and `verification_result`.
- **GET `/{contract_id}/review-queue`**: Return flags currently paused at the human review gate by inspecting the `verification_result` for unverified/high-risk items.
- **POST `/{contract_id}/review`**: Refactor `log_audit_event` from `scripts/resume_review.py` into a shared utility. Save human override to `audit_log`, update the LangGraph state with `graph.update_state`, and resume execution.
- **POST `/{contract_id}/negotiate`**: Directly invoke `run_negotiation_node` from `agents/negotiation_simulation.py` for a specific approved flag and return the `negotiation_transcript`.

### 2. N8N Webhook Automation
#### [NEW] [automation/n8n_high_risk_webhook.json](file:///d:/Coding/themis/automation/n8n_high_risk_webhook.json)
- Create a mock n8n workflow exported as JSON that listens on a webhook (e.g., `http://localhost:5678/webhook/high-risk-flag`) and writes the payload to a local file (using "Write to File" node).
#### [MODIFY] [api/routers/contracts.py](file:///d:/Coding/themis/api/routers/contracts.py) (or `verification_agent`)
- When the graph detects a high-risk or unverified flag, dispatch an HTTP POST request to `N8N_WEBHOOK_URL` containing the flag details.

### 3. Docker Compose
#### [MODIFY] [docker-compose.yml](file:///d:/Coding/themis/docker-compose.yml)
- Flesh out the `api` service to run FastAPI on port 8000 alongside Neo4j and Qdrant.

### 4. Integration Tests
#### [NEW] [tests/integration/test_tenant_isolation.py](file:///d:/Coding/themis/tests/integration/test_tenant_isolation.py)
- Spin up two mock tenants using mocked JWT tokens. Prove Tenant A gets a 403/404 or empty data when requesting Tenant B's contract via `/contracts/{contract_id}/results`.

#### [NEW] [tests/integration/test_day7_api.py](file:///d:/Coding/themis/tests/integration/test_day7_api.py)
- Use `fastapi.testclient.TestClient`.
- Hit `/upload` with SaaS MSA text.
- Poll `/status` until `awaiting_review`.
- Hit `/review-queue` and verify items.
- Submit `/review`.
- Hit `/results` and assert structure.
- Assert that n8n webhook was fired (e.g., check that the workflow's local file write occurred).

## Verification Plan
1. Start the FastAPI server locally (`uvicorn api.main:app`).
2. Run `curl` to `POST /contracts/upload` with the SaaS MSA and capture the JSON response.
3. Poll the API via script and capture status transitions.
4. Run `test_tenant_isolation.py` and print raw output.
5. Run `test_day7_api.py` via pytest and print raw output.
6. Verify the n8n JSON file and the resulting text file written by the n8n webhook.
