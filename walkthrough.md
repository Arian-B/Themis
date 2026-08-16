# Themis Build Walkthrough

## Day 6: Negotiation Simulation & Critic Feedback Loop

### 1. Negotiation Simulation Agent (Agent 6)
We implemented a genuine LangGraph cycle that simulates a back-and-forth legal negotiation over high-risk contract clauses. 
- A `proposer_node` and `counterparty_node` iteratively propose and critique redlined clauses.
- The loop routes conditionally, ending either when a mutually acceptable agreement is reached or after a 4-turn impasse (max turns).
- We wired this up in `graph/build.py` as an optional path, strictly gated by the human reviewer: it only runs if the human reviewer explicitly accepts a flag and requests it.

### 2. Critic Feedback Agent (Agent 7)
We implemented an offline Critic Agent that extracts structured lessons from human override decisions in the `audit_log` to tune future system models.
- It queries Supabase for `flag.overridden` events.
- Evaluates the human's decision against the original flagged concern to determine utility and deduce a generalizable lesson.
- Saves these lessons to a newly migrated `critic_lessons` table in Supabase.

### Integration Tests and Results
- The integration test successfully simulated a 4-turn negotiation over the SaaS MSA auto-renewal clause.
- The Critic Agent successfully ran against the real Day 5 audit log and extracted four unique legal lessons.
