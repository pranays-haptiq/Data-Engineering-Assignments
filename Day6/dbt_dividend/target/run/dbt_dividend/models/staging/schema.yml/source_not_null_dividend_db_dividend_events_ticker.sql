
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ticker
from "postgres"."public"."dividend_events"
where ticker is null



  
  
      
    ) dbt_internal_test