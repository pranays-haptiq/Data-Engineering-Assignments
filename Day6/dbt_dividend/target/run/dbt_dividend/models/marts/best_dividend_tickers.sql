
  
    

  create  table "postgres"."public"."best_dividend_tickers__dbt_tmp"
  
  
    as
  
  (
    

/*
  The 2 best tickers are those with:
    1. The highest % of dividend events where price_drop < dividend_amount
    2. At least 3 qualifying events to ensure statistical relevance
*/
select
    ticker,
    total_events,
    favorable_events,
    favorable_pct,
    avg_dividend,
    avg_price_drop,
    first_event_date,
    last_event_date
from "postgres"."public"."fct_dividend_performance"
where total_events >= 3
order by favorable_pct desc, avg_dividend desc
limit 2
  );
  