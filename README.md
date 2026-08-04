# Themis

**Multi-agent legal & compliance intelligence platform for SMBs.**

A portfolio-defining capstone project demonstrating production-grade AI/ML engineering:
LangGraph state machines, retrieval-grounded reasoning, atomic fact verification,
knowledge graph memory, adversarial negotiation simulation, and regulatory monitoring.

---

## Architecture

```
PDF Upload
    │
    ▼
┌─────────────────────────────────────────────────┐
│            LangGraph StateGraph                 │
│                                                 │
│  ① Jurisdiction Classifier (Ollama)             │
│        │                                        │
│  ② Extraction Agent (Ollama + pdfplumber)       │
│        │                                        │
│  ③ Risk Analysis Agent (Claude + RAG/MCP)       │
│        │                                        │
│  ④ Atomic Verification Agent (Claude)           │
│        │             ← interrupt_before (HITL)  │
│  ⑤ KG Writer (Neo4j via MCP)                   │
│        │                                        │
│  ⑥ Negotiation Simulation (Claude × 2, cycle)  │
│                                                 │
│  ⑦ Regulatory Monitoring (background, cron)    │
│  ⑧ Critic / Feedback (HITL correction log)     │
└─────────────────────────────────────────────────┘
    │
    ▼
FastAPI → React Frontend
```

## Tech Stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (real cycles + interrupt_before) |
| Schema enforcement | PydanticAI at every agent boundary |
| Tool layer | MCP servers (not ad-hoc @tool wrappers) |
| Vector store | Qdrant (LangChain abstraction) |
| Knowledge graph | Neo4j (LangChain abstraction) |
| Local inference | Ollama (llama3.1:8b, nomic-embed-text) |
| Complex reasoning | Claude claude-3-5-sonnet (Anthropic API) |
| PII handling | Microsoft Presidio |
| Observability | Langfuse (self-hosted) |
| Evaluation | Ragas (RAG quality metrics) |
| Automation | n8n workflows |
| Backend | FastAPI (multi-tenant, JWT) |
| Frontend | React + Vite |
| Infra | Docker → Kubernetes, Terraform, GitHub Actions |

## Quick Start (Local Dev)

```bash
# 1. Clone and enter directory
git clone <repo> && cd themis

# 2. Copy and fill environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY and generated secrets

# 3. Start infrastructure
docker compose up -d

# 4. Pull Ollama models (first time only, ~5GB)
docker compose exec ollama ollama pull llama3.1:8b
docker compose exec ollama ollama pull nomic-embed-text

# 5. Install Python dependencies (for local dev outside Docker)
pip install -e ".[api,dev]"
python -m spacy download en_core_web_lg

# 6. Set up pre-commit hooks
pre-commit install

# 7. Run tests
pytest tests/unit/ -v
```

## Service URLs (local)

| Service | URL |
|---|---|
| FastAPI (Swagger) | http://localhost:8000/docs |
| Qdrant UI | http://localhost:6333/dashboard |
| Neo4j Browser | http://localhost:7474 |
| Langfuse | http://localhost:3000 |
| n8n | http://localhost:5678 |
| Ollama API | http://localhost:11434 |

## Repository Structure

See [`implementation_plan.md`](implementation_plan.md) for the full phased build plan
and component descriptions.

```
themis/
├── agents/          # LangGraph agent nodes (8 agents)
├── graph/           # StateGraph wiring, state TypedDict, routers
├── schemas/         # PydanticAI models for every agent boundary
├── retrieval/       # Qdrant + Neo4j abstractions, corpus loaders
├── tools/mcp/       # MCP servers (retrieval, KG, monitoring)
├── api/             # FastAPI app, routers, middleware
├── observability/   # Langfuse tracing integration
├── eval/            # Ragas RAG quality evaluation
├── automation/      # n8n workflow JSON exports
├── frontend/        # React + Vite UI
├── infra/           # Terraform + Kubernetes manifests
└── tests/           # Unit + integration test suites
```

## Build Phases

| Phase | Goal | Status |
|---|---|---|
| 0 | Infrastructure skeleton (Docker, CI) | ✅ Scaffolded |
| 1 | Core LangGraph loop (3 agents, end-to-end) | 🔲 Next |
| 2 | RAG layer (Qdrant + Neo4j + retrieval) | 🔲 Pending |
| 3 | Advanced agents (verification, KG, negotiation, monitoring) | 🔲 Pending |
| 4 | Frontend + API hardening | 🔲 Pending |
| 5 | Observability, evaluation, automation | 🔲 Pending |
| 6 | Kubernetes + Terraform + CI/CD | 🔲 Pending |

## Interview Talking Points

- **Why LangGraph over a linear chain?** Real cycles (negotiation subgraph), interrupt_before
  for human-in-the-loop, checkpointed state for resumability — can't do these with a chain.
- **Why MCP for tools?** Protocol-standard, swappable, callable by any MCP client (LangGraph,
  Claude Desktop, n8n) — not locked to LangChain internals.
- **Why atomic verification?** Every claim shown to the user has a provenance trail.
  The two-pass (generate → verify) is what separates this from a naive "ask the LLM" tool.
- **Why self-hosted Langfuse?** Contract data is PII-sensitive; no third-party trace storage.
- **Multi-tenant isolation:** Qdrant collection-per-tenant-jurisdiction; Neo4j WHERE tenant_id
  filter on every query; JWT-bound tenant context propagated through the entire call stack.
