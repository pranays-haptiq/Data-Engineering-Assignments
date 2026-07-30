
  
    

  create  table "postgres"."public"."fct_dividend_performance__dbt_tmp"
  
  
    as
  
  (
    

with base as (
    select
        ticker,
        count(*)                                                as total_events,
        sum(case when drop_less_than_div then 1 else 0 end)     as favorable_events,
        avg(dividend_amount)                                    as avg_dividend,
        avg(price_drop)                                         as avg_price_drop,
        min(ex_date)                                            as first_event_date,
        max(ex_date)                                            as last_event_date
    from "postgres"."public"."stg_dividend_events"
    group by ticker
)

select
    ticker,
    total_events,
    favorable_events,
    round(
        favorable_events::numeric / nullif(total_events, 0) * 100,
        2
    )                                   as favorable_pct,
    round(avg_dividend::numeric, 4)     as avg_dividend,
    round(avg_price_drop::numeric, 4)   as avg_price_drop,
    first_event_date,
    last_event_date
from base
  );
  