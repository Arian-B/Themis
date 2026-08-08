-- =============================================================================
-- Themis — Initial Database Schema
-- Migration: 001_initial_schema.sql
-- Target: Supabase (PostgreSQL 15+)
-- =============================================================================
-- Run with:
--   psql $DATABASE_URL -f supabase/migrations/001_initial_schema.sql
-- Or apply via Supabase CLI:
--   supabase db push
-- =============================================================================
-- Design principles:
--   1. Row-Level Security (RLS) is enabled on all tenant-scoped tables.
--      API access uses the anon/service_role keys — RLS policies enforce
--      that a user can only read/write rows belonging to their tenant.
--   2. audit_log is append-only (no UPDATE/DELETE). Triggers enforce this.
--   3. UUIDs as primary keys throughout (compatible with Supabase Auth user IDs).
--   4. contract_status and flag_severity use CHECK constraints rather than
--      ENUM types to make future additions a simple ALTER TABLE, not a type
--      migration.
--   5. All timestamps stored as TIMESTAMPTZ (UTC). Application layer converts
--      to user timezone for display.
-- =============================================================================

-- Ensure uuid-ossp extension (Supabase enables this by default; included for
-- completeness when running against a plain Postgres instance)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- 1. tenants
--    One row per organisation using Themis. All other tables FK to this.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.tenants (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT        NOT NULL,
    slug            TEXT        NOT NULL UNIQUE,   -- URL-safe identifier, e.g. "acme-corp"
    plan            TEXT        NOT NULL DEFAULT 'trial'
                    CHECK (plan IN ('trial', 'starter', 'professional', 'enterprise')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    settings        JSONB       NOT NULL DEFAULT '{}',   -- tenant-level config (jurisdiction prefs, etc.)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.tenants                IS 'Organisations using the Themis platform.';
COMMENT ON COLUMN public.tenants.slug           IS 'URL-safe unique identifier used in API paths and Qdrant collection names.';
COMMENT ON COLUMN public.tenants.settings       IS 'JSON bag for tenant-specific config: default_jurisdiction, notification_prefs, etc.';

-- Auto-update updated_at on any row change
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

CREATE TRIGGER tenants_updated_at
    BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- 2. users
--    Maps Supabase Auth UIDs to tenant membership + role.
--    One user can belong to exactly one tenant (MVP; multi-tenancy via tenant_id).
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.users (
    id              UUID PRIMARY KEY,               -- Supabase Auth user ID (auth.users.id)
    tenant_id       UUID        NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email           TEXT        NOT NULL,
    display_name    TEXT,
    role            TEXT        NOT NULL DEFAULT 'member'
                    CHECK (role IN ('owner', 'admin', 'member', 'viewer')),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.users              IS 'Application users, linked to Supabase Auth by UUID.';
COMMENT ON COLUMN public.users.id          IS 'Matches auth.users.id — used as the FK from Supabase Auth JWT sub claim.';
COMMENT ON COLUMN public.users.role        IS 'owner: full admin; admin: manage users/contracts; member: create/view; viewer: read-only.';

CREATE INDEX IF NOT EXISTS users_tenant_id_idx ON public.users(tenant_id);

CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- 3. contracts
--    Metadata record for every contract uploaded by a tenant.
--    The actual PDF bytes are stored in Supabase Storage (not in this table).
--    The analysis output (RiskReport) is stored in the `analysis_result` JSONB column.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.contracts (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID        NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    uploaded_by         UUID        NOT NULL REFERENCES public.users(id),
    -- File metadata
    filename            TEXT        NOT NULL,
    storage_path        TEXT        NOT NULL,   -- Supabase Storage object path
    file_size_bytes     BIGINT,
    -- Classification
    jurisdiction        TEXT        NOT NULL DEFAULT 'us_generic',
    contract_type       TEXT,                  -- e.g. "nda", "msa", "lease", "employment"
    counterparty_name   TEXT,                  -- extracted by Extraction Agent
    effective_date      DATE,                  -- extracted by Extraction Agent
    expiry_date         DATE,                  -- extracted by Extraction Agent (if present)
    -- Pipeline state
    status              TEXT        NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'archived')),
    session_id          UUID        NOT NULL DEFAULT uuid_generate_v4(),   -- ties Langfuse traces
    -- Analysis output
    analysis_result     JSONB,                 -- RiskReport schema from schemas/risk_report.py
    risk_score          NUMERIC(4,2),          -- 0.00–10.00; NULL until analysis complete
    -- Timestamps
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    analyzed_at         TIMESTAMPTZ            -- set when status → completed
);

COMMENT ON TABLE  public.contracts                  IS 'Contract upload records. PDF stored in Supabase Storage; analysis in analysis_result JSONB.';
COMMENT ON COLUMN public.contracts.storage_path     IS 'Supabase Storage object path: contracts/{tenant_id}/{id}/{filename}';
COMMENT ON COLUMN public.contracts.session_id       IS 'UUID correlating all Langfuse trace events for this analysis run.';
COMMENT ON COLUMN public.contracts.analysis_result  IS 'Full RiskReport JSON from the LangGraph pipeline. Schema defined in schemas/risk_report.py.';
COMMENT ON COLUMN public.contracts.risk_score       IS 'Aggregate risk score 0–10 extracted from analysis_result for quick dashboard queries.';

CREATE INDEX IF NOT EXISTS contracts_tenant_id_idx     ON public.contracts(tenant_id);
CREATE INDEX IF NOT EXISTS contracts_status_idx        ON public.contracts(status);
CREATE INDEX IF NOT EXISTS contracts_uploaded_by_idx   ON public.contracts(uploaded_by);
CREATE INDEX IF NOT EXISTS contracts_jurisdiction_idx  ON public.contracts(jurisdiction);
CREATE INDEX IF NOT EXISTS contracts_expiry_date_idx   ON public.contracts(expiry_date)
    WHERE expiry_date IS NOT NULL;

CREATE TRIGGER contracts_updated_at
    BEFORE UPDATE ON public.contracts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- 4. flags
--    Individual risk flags surfaced by the Risk Analysis Agent.
--    Separate table (not nested in contracts.analysis_result) so they can be
--    queried, filtered, and human-overridden without re-parsing the full JSONB.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.flags (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    contract_id     UUID        NOT NULL REFERENCES public.contracts(id) ON DELETE CASCADE,
    tenant_id       UUID        NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    -- Flag content
    clause_type     TEXT        NOT NULL,  -- e.g. "limitation_of_liability", "indemnification"
    severity        TEXT        NOT NULL
                    CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    title           TEXT        NOT NULL,  -- Short description: "Missing liability cap"
    description     TEXT        NOT NULL,  -- Detailed explanation shown in the UI
    -- Grounding (every claim must be traceable)
    source_text     TEXT,                  -- The exact contract clause that triggered this flag
    chunk_id        TEXT,                  -- Qdrant chunk_id for retrieval grounding
    citation_url    TEXT,                  -- URL to the statute / regulation cited
    -- Verification
    verified        BOOLEAN     NOT NULL DEFAULT FALSE,  -- True if AtomicVerifier passed
    verification_score  NUMERIC(4,2),     -- 0.00–1.00 confidence from verification agent
    -- Human override
    human_override  TEXT
                    CHECK (human_override IN ('accepted', 'rejected', 'escalated') OR human_override IS NULL),
    override_by     UUID        REFERENCES public.users(id),
    override_at     TIMESTAMPTZ,
    override_note   TEXT,
    -- Timestamps
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.flags                  IS 'Risk flags surfaced by the analysis pipeline. One flag per identified risk clause.';
COMMENT ON COLUMN public.flags.source_text      IS 'Verbatim contract text that triggered this flag — required for grounded claims.';
COMMENT ON COLUMN public.flags.chunk_id         IS 'Qdrant chunk_id used for retrieval grounding; links flag to corpus evidence.';
COMMENT ON COLUMN public.flags.verified         IS 'True when AtomicVerifier agent confirmed the claim at the atomic-fact level.';
COMMENT ON COLUMN public.flags.human_override   IS 'Legal team disposition: accepted (risk acknowledged), rejected (false positive), escalated.';

CREATE INDEX IF NOT EXISTS flags_contract_id_idx ON public.flags(contract_id);
CREATE INDEX IF NOT EXISTS flags_tenant_id_idx   ON public.flags(tenant_id);
CREATE INDEX IF NOT EXISTS flags_severity_idx    ON public.flags(severity);
CREATE INDEX IF NOT EXISTS flags_verified_idx    ON public.flags(verified);
CREATE INDEX IF NOT EXISTS flags_override_idx    ON public.flags(human_override) WHERE human_override IS NOT NULL;

CREATE TRIGGER flags_updated_at
    BEFORE UPDATE ON public.flags
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- =============================================================================
-- 5. audit_log
--    Append-only immutable log of all sensitive actions.
--    Used for compliance evidence and human-override audit trails.
--    RLS: users can INSERT (their own actions); no one can UPDATE or DELETE.
-- =============================================================================

CREATE TABLE IF NOT EXISTS public.audit_log (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    tenant_id       UUID        NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    actor_id        UUID        REFERENCES public.users(id),   -- NULL for system actions
    action          TEXT        NOT NULL,   -- e.g. "contract.uploaded", "flag.overridden"
    resource_type   TEXT        NOT NULL,   -- "contract" | "flag" | "user" | "tenant"
    resource_id     UUID,                   -- ID of the affected resource
    details         JSONB       NOT NULL DEFAULT '{}',   -- action-specific payload
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  public.audit_log              IS 'Append-only compliance log. All contract uploads, analysis runs, and human overrides are recorded here.';
COMMENT ON COLUMN public.audit_log.actor_id     IS 'NULL for automated system actions (pipeline runs, scheduled jobs).';
COMMENT ON COLUMN public.audit_log.action       IS 'Dot-notation action name: <resource_type>.<verb>. E.g. contract.uploaded, flag.overridden, user.invited.';
COMMENT ON COLUMN public.audit_log.details      IS 'Action-specific payload, e.g. {old_status, new_status} for status transitions.';

-- Partial index for fast per-tenant audit queries
CREATE INDEX IF NOT EXISTS audit_log_tenant_id_idx      ON public.audit_log(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS audit_log_resource_idx       ON public.audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS audit_log_actor_id_idx       ON public.audit_log(actor_id) WHERE actor_id IS NOT NULL;

-- Prevent any UPDATE or DELETE on audit_log (enforced at DB level, not just RLS)
CREATE OR REPLACE RULE audit_log_no_update AS
    ON UPDATE TO public.audit_log DO INSTEAD NOTHING;

CREATE OR REPLACE RULE audit_log_no_delete AS
    ON DELETE TO public.audit_log DO INSTEAD NOTHING;

-- =============================================================================
-- 6. Row-Level Security (RLS)
--    Policies use auth.uid() (Supabase JWT sub) and a helper function to
--    resolve the current user's tenant_id.
-- =============================================================================

-- Helper: resolve current user's tenant_id from the users table
CREATE OR REPLACE FUNCTION public.current_tenant_id()
RETURNS UUID LANGUAGE sql STABLE SECURITY DEFINER AS $$
    SELECT tenant_id FROM public.users WHERE id = auth.uid() LIMIT 1;
$$;

-- Enable RLS on all tenant-scoped tables
ALTER TABLE public.tenants   ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.users     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.contracts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.flags     ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.audit_log ENABLE ROW LEVEL SECURITY;

-- tenants: users can only see their own tenant
CREATE POLICY tenants_isolation ON public.tenants
    USING (id = public.current_tenant_id());

-- users: users can only see members of their own tenant
CREATE POLICY users_isolation ON public.users
    USING (tenant_id = public.current_tenant_id());

-- contracts: tenant isolation
CREATE POLICY contracts_isolation ON public.contracts
    USING (tenant_id = public.current_tenant_id());

-- flags: tenant isolation
CREATE POLICY flags_isolation ON public.flags
    USING (tenant_id = public.current_tenant_id());

-- audit_log: read own tenant; insert own actions
CREATE POLICY audit_log_read ON public.audit_log
    FOR SELECT USING (tenant_id = public.current_tenant_id());

CREATE POLICY audit_log_insert ON public.audit_log
    FOR INSERT WITH CHECK (tenant_id = public.current_tenant_id());

-- Service role bypasses RLS (used by FastAPI backend with service_role_key)
-- No additional policy needed — service role always bypasses RLS by Supabase default.

-- =============================================================================
-- 7. Seed data (development only)
--    Creates a single demo tenant + owner user for local development.
--    Gated on PGAPPNAME='themis-seed' to prevent accidental production seed.
-- =============================================================================

DO $$
BEGIN
    IF current_setting('application_name', TRUE) = 'themis-seed' THEN
        -- Demo tenant
        INSERT INTO public.tenants (id, name, slug, plan)
        VALUES (
            '00000000-0000-0000-0000-000000000001'::UUID,
            'Acme Corp (Demo)',
            'acme-demo',
            'professional'
        )
        ON CONFLICT (id) DO NOTHING;

        RAISE NOTICE 'Seed data inserted for development.';
    END IF;
END;
$$;
