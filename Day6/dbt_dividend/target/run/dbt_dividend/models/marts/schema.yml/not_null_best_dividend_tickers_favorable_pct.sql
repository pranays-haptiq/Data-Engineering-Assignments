
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select favorable_pct
from "postgres"."public"."best_dividend_tickers"
where favorable_pct is null



  
  
      
    ) dbt_internal_test