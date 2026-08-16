# Day 6 Implementation Plan: Negotiation Simulation + Critic Feedback Loop

## Objective
Implement Day 6 deliverables: a genuine LangGraph cycle for negotiation simulation and a critic feedback agent that processes human override decisions from the `audit_log` into reusable lessons.

## Proposed Changes

### 1. Schemas
#### [MODIFY] [schemas/negotiation.py](file:///d:/Coding/themis/schemas/negotiation.py)
- Define `NegotiationTurn`: `turn_number`, `speaker` (Literal["proposer", "counterparty"]), `proposed_text`, `rationale`
- Define `NegotiationTranscript`: `clause_id`, `turns: list[NegotiationTurn]`, `outcome` (Literal["agreement_reached", "impasse", "max_turns_reached"])

#### [MODIFY] [schemas/feedback.py](file:///d:/Coding/themis/schemas/feedback.py)
- Define `CriticFeedback`: `flag_id`, `human_decision`, `was_flag_useful: bool`, `lesson: str`

### 2. Supabase Migration
#### [NEW] [supabase/migrations/002_critic_lessons.sql](file:///d:/Coding/themis/supabase/migrations/002_critic_lessons.sql)
- Create `critic_lessons` table with columns: `id`, `flag_id`, `human_decision`, `was_flag_useful`, `lesson`, `created_at`.

### 3. Agents
#### [NEW] [agents/negotiation_simulation.py](file:///d:/Coding/themis/agents/negotiation_simulation.py)
- Implement a `StateGraph` subgraph that takes the flagged clause and loops between a `proposer_node` and a `counterparty_node`.
- Use a conditional edge `route_negotiation` that checks if an agreement was reached or max turns (4) was hit.
- Expose a `run_negotiation` function that can be added to the main graph.

#### [NEW] [agents/critic_agent.py](file:///d:/Coding/themis/agents/critic_agent.py)
- Script/Agent that fetches rows from `audit_log` where `action = 'flag.overridden'`.
- Uses an LLM to generate `CriticFeedback` based on the original concern and the human decision.
- Writes the generated feedback to the `critic_lessons` table.

### 4. Graph Wiring
#### [MODIFY] [graph/build.py](file:///d:/Coding/themis/graph/build.py)
- Add `negotiation_simulation` node.
- Add a conditional edge after `human_review`: if a human requested negotiation for any flag (via `human_override` state), route to `negotiation_simulation`, else route to `knowledge_graph_writer`.
- From `negotiation_simulation`, route to `knowledge_graph_writer`.

### 5. Tests
#### [NEW] [tests/integration/test_day6_negotiation.py](file:///d:/Coding/themis/tests/integration/test_day6_negotiation.py)
- Test the `negotiation_simulation` subgraph explicitly with the known auto-renewal flag (flag 14) from the SaaS MSA.
- Assert that the transcript has >1 turns and terminates correctly.

### 6. Execution & Verification
- Execute `test_day6_negotiation.py` and print the raw transcript.
- Run `agents/critic_agent.py` on the 3 audit_log entries (flag index 0, 7, 14) to populate `critic_lessons`.
- Query `critic_lessons` and print the rows to verify the critic loop worked.

## Verification Plan
- `pytest tests/integration/test_day6_negotiation.py -v -s`
- Run `agents/critic_agent.py` directly and query the Supabase DB to show raw `critic_lessons`.
