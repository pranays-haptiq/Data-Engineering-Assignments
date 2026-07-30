
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select dividend_amount
from "postgres"."public"."dividend_events"
where dividend_amount is null



  
  
      
    ) dbt_internal_test