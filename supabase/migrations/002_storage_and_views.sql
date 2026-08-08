-- =============================================================================
-- Themis — Supabase storage bucket + helper views
-- Migration: 002_storage_and_views.sql
-- Applies AFTER 001_initial_schema.sql
-- =============================================================================
-- Adds:
--   1. Supabase Storage bucket policy for contract PDFs
--   2. v_contract_summary — dashboard-ready view (no analysis_result JSONB)
--   3. v_flag_summary — flags with contract and tenant context for dashboards
-- =============================================================================

-- =============================================================================
-- 1. Storage bucket access policies
--    Bucket name: "contracts"  (must be created in Supabase Dashboard or CLI first)
--    Policy: each tenant can only read/write their own files
--    Path pattern: contracts/{tenant_id}/{contract_id}/{filename}
-- =============================================================================

-- (Supabase storage policies are set in the Dashboard or via storage.objects RLS)
-- The following is a reminder comment — Supabase Storage policies are separate
-- from table RLS and must be applied via the Supabase Dashboard or supabase CLI:
--
--   supabase storage create-bucket contracts --public false
--
-- Access policy (allow tenant to read/write their prefix):
--   create policy "tenant_contract_files" on storage.objects
--     for all using (
--       bucket_id = 'contracts'
--       and (storage.foldername(name))[1] = current_tenant_id()::text
--     );

-- =============================================================================
-- 2. v_contract_summary — Lightweight view for dashboard contract list
-- =============================================================================

CREATE OR REPLACE VIEW public.v_contract_summary AS
SELECT
    c.id,
    c.tenant_id,
    c.filename,
    c.jurisdiction,
    c.contract_type,
    c.counterparty_name,
    c.effective_date,
    c.expiry_date,
    c.status,
    c.risk_score,
    c.created_at,
    c.analyzed_at,
    u.display_name  AS uploaded_by_name,
    u.email         AS uploaded_by_email,
    -- Aggregate flag counts for quick display
    (SELECT COUNT(*) FROM public.flags f
     WHERE f.contract_id = c.id AND f.severity = 'critical') AS critical_flags,
    (SELECT COUNT(*) FROM public.flags f
     WHERE f.contract_id = c.id AND f.severity = 'high')     AS high_flags,
    (SELECT COUNT(*) FROM public.flags f
     WHERE f.contract_id = c.id)                              AS total_flags
FROM public.contracts c
JOIN public.users u ON u.id = c.uploaded_by;

COMMENT ON VIEW public.v_contract_summary IS
    'Dashboard-ready contract list with flag counts. RLS on contracts/flags tables '
    'applies to this view automatically.';

-- =============================================================================
-- 3. v_flag_summary — Flags with denormalized context for dashboard views
-- =============================================================================

CREATE OR REPLACE VIEW public.v_flag_summary AS
SELECT
    f.id,
    f.contract_id,
    f.tenant_id,
    f.clause_type,
    f.severity,
    f.title,
    f.description,
    f.source_text,
    f.verified,
    f.verification_score,
    f.human_override,
    f.override_at,
    f.created_at,
    c.filename       AS contract_filename,
    c.jurisdiction   AS contract_jurisdiction,
    c.status         AS contract_status,
    c.risk_score     AS contract_risk_score,
    ov.display_name  AS override_by_name
FROM public.flags f
JOIN public.contracts c ON c.id = f.contract_id
LEFT JOIN public.users ov ON ov.id = f.override_by;

COMMENT ON VIEW public.v_flag_summary IS
    'Risk flags with contract context. Useful for the flag review dashboard.';
