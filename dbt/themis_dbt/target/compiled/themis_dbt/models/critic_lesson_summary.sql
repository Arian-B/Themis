

with lessons as (
  select
    cl.flag_id,
    cl.human_decision,
    cl.was_flag_useful,
    cl.lesson,
    cl.created_at
  from critic_lessons cl
),

lesson_stats as (
  select
    count(*) as total_lessons,
    count(case when was_flag_useful then 1 end) as useful_count,
    count(case when not was_flag_useful then 1 end) as not_useful_count,
    min(created_at) as first_lesson,
    max(created_at) as latest_lesson
  from lessons
),

decision_breakdown as (
  select
    human_decision,
    count(*) as count,
    round(100.0 * count(*) / sum(count(*)) over (), 2) as pct
  from lessons
  group by human_decision
)

select
  'summary' as scope,
  total_lessons,
  useful_count,
  not_useful_count,
  round(100.0 * useful_count / nullif(total_lessons, 0), 2) as usefulness_rate_pct,
  first_lesson,
  latest_lesson,
  null as human_decision
from lesson_stats

union all

select
  'by_decision' as scope,
  count as total_lessons,
  0 as useful_count,
  0 as not_useful_count,
  pct as usefulness_rate_pct,
  null as first_lesson,
  null as latest_lesson,
  human_decision
from decision_breakdown

order by scope, human_decision