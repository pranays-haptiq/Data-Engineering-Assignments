

/*
  Full dividend event history (last 5 years) for the 2 best tickers only.
*/
select
    e.ticker,
    e.ex_date,
    e.dividend_amount,
    e.price_day_before,
    e.price_on_ex_date,
    e.price_drop,
    e.drop_less_than_div,
    p.favorable_pct,
    p.avg_dividend
from "postgres"."public"."stg_dividend_events" e
inner join "postgres"."public"."best_dividend_tickers" b
    on e.ticker = b.ticker
inner join "postgres"."public"."fct_dividend_performance" p
    on e.ticker = p.ticker
where e.ex_date >= current_date - interval '5 years'
order by e.ticker, e.ex_date