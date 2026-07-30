
    
    

select
    ticker as unique_field,
    count(*) as n_records

from "postgres"."public"."fct_dividend_performance"
where ticker is not null
group by ticker
having count(*) > 1


