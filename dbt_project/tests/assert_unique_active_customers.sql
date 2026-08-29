-- Detect if any customer_id has multiple active versions
-- This would cause revenue inflation in fct_daily_revenue due to the left join
select customer_id, count(*) as version_count
from {{ ref('stg_customers') }}
where is_active = true
group by customer_id
having count(*) > 1
