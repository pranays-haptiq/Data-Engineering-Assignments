
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select ex_date
from "postgres"."public"."dividend_events"
where ex_date is null



  
  
      
    ) dbt_internal_test