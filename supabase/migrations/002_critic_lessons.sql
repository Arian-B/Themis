-- =============================================================================
-- 002_critic_lessons.sql
-- Day 6: Critic Feedback Loop
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.critic_lessons (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flag_id         UUID NOT NULL,
    human_decision  TEXT NOT NULL,
    was_flag_useful BOOLEAN NOT NULL,
    lesson          TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE public.critic_lessons IS 'Lessons learned by the Critic Agent from human overrides.';

-- Partial index for fast queries by flag
CREATE INDEX IF NOT EXISTS critic_lessons_flag_id_idx ON public.critic_lessons(flag_id);

-- Enable RLS
ALTER TABLE public.critic_lessons ENABLE ROW LEVEL SECURITY;

-- Note: In a real multi-tenant setup, we'd add tenant_id to this table and use the same RLS policies as Day 1.
-- Since the prompt does not require a tenant_id here, and to keep it simple, we allow service role to bypass RLS.
