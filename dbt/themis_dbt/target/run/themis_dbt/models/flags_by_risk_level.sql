
  
    

  create  table "postgres"."public"."flags_by_risk_level__dbt_tmp"
  
  
    as
  
  (
    

with audit_flags as (
  select
    al.resource_id as flag_id,
    al.action,
    al.details->>'concern' as concern,
    al.details->>'human_override' as decision,
    al.details->>'original_risk' as risk_level,
    al.created_at
  from audit_log al
  where al.action in ('flag.accepted', 'flag.overridden', 'flag.rejected')
    and al.details ? 'concern'
),

flag_aggregation as (
  select
    risk_level,
    count(*) as total_flags,
    count(case when decision = 'accepted' then 1 end) as accepted_count,
    count(case when decision = 'rejected' then 1 end) as rejected_count,
    count(case when decision = 'overridden' then 1 end) as overridden_count,
    min(created_at) as first_seen,
    max(created_at) as last_seen
  from audit_flags
  group by risk_level
)

select
  risk_level,
  total_flags,
  accepted_count,
  rejected_count,
  overridden_count,
  first_seen,
  last_seen,
  round(100.0 * accepted_count / nullif(total_flags, 0), 2) as acceptance_rate_pct,
  round(100.0 * rejected_count / nullif(total_flags, 0), 2) as rejection_rate_pct,
  round(100.0 * overridden_count / nullif(total_flags, 0), 2) as override_rate_pct
from flag_aggregation
order by
  case risk_level
    when 'critical' then 1
    when 'high' then 2
    when 'medium' then 3
    when 'low' then 4
    else 5
  end
  );
  