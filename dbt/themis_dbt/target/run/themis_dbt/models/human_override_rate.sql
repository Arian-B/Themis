
  
    

  create  table "postgres"."public"."human_override_rate__dbt_tmp"
  
  
    as
  
  (
    

with review_decisions as (
  select
    al.resource_id as flag_id,
    al.details->>'concern' as concern,
    al.details->>'human_override' as decision,
    al.details->>'original_risk' as risk_level,
    al.details->>'contract_id' as contract_id,
    al.created_at
  from audit_log al
  where al.action in ('flag.accepted', 'flag.overridden', 'flag.rejected')
    and al.details ? 'human_override'
),

contract_stats as (
  select
    contract_id,
    count(*) as total_reviews,
    count(case when decision = 'accepted' then 1 end) as accepted_count,
    count(case when decision = 'rejected' then 1 end) as rejected_count,
    count(case when decision = 'overridden' then 1 end) as overridden_count,
    min(created_at) as first_review,
    max(created_at) as last_review
  from review_decisions
  group by contract_id
),

overall_stats as (
  select
    count(*) as total_reviews,
    count(case when decision = 'accepted' then 1 end) as total_accepted,
    count(case when decision = 'rejected' then 1 end) as total_rejected,
    count(case when decision = 'overridden' then 1 end) as total_overridden,
    count(distinct contract_id) as contracts_reviewed,
    min(created_at) as first_review,
    max(created_at) as last_review
  from review_decisions
)

select
  'overall' as scope,
  null as contract_id,
  total_reviews,
  total_accepted,
  total_rejected,
  total_overridden,
  contracts_reviewed,
  round(100.0 * total_accepted / nullif(total_reviews, 0), 2) as acceptance_rate_pct,
  round(100.0 * total_rejected / nullif(total_reviews, 0), 2) as rejection_rate_pct,
  round(100.0 * total_overridden / nullif(total_reviews, 0), 2) as override_rate_pct,
  first_review,
  last_review
from overall_stats

union all

select
  'per_contract' as scope,
  contract_id,
  total_reviews,
  accepted_count,
  rejected_count,
  overridden_count,
  null as contracts_reviewed,
  round(100.0 * accepted_count / nullif(total_reviews, 0), 2) as acceptance_rate_pct,
  round(100.0 * rejected_count / nullif(total_reviews, 0), 2) as rejection_rate_pct,
  round(100.0 * overridden_count / nullif(total_reviews, 0), 2) as override_rate_pct,
  first_review,
  last_review
from contract_stats

order by scope, contract_id
  );
  