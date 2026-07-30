{{ config(materialized='view') }}

select
    ticker,
    ex_date,
    dividend_amount,
    price_day_before,
    price_on_ex_date,
    price_drop,
    drop_less_than_div
from {{ source('dividend_db', 'dividend_events') }}
where dividend_amount > 0
  and price_day_before is not null
  and price_on_ex_date is not null
