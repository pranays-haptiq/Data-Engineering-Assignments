
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ticker
from "postgres"."public"."stg_dividend_events"
where ticker is null



  
  
      
    ) dbt_internal_test