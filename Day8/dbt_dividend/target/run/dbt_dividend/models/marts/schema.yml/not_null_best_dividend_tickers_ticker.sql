
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ticker
from "postgres"."public"."best_dividend_tickers"
where ticker is null



  
  
      
    ) dbt_internal_test