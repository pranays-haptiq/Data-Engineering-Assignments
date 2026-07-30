
    
    

select
    ticker as unique_field,
    count(*) as n_records

from "postgres"."public"."best_dividend_tickers"
where ticker is not null
group by ticker
having count(*) > 1


