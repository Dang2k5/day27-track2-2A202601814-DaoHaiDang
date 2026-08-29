-- Ensure we have order data from recent dates (last 30 days)
-- Catches stale data or missing records
select 'stale_data' as issue
from (
    select max(order_date) as latest_date
    from {{ ref('fct_daily_revenue') }}
) t
where current_date - latest_date > 30
