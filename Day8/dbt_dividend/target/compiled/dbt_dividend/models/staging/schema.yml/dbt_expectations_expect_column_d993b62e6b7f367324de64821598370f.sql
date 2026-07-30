






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and price_drop >= -500 and price_drop <= 500
)
 as expression


    from "postgres"."public"."stg_dividend_events"
    

),
validation_errors as (

    select
        *
    from
        grouped_expression
    where
        not(expression = true)

)

select *
from validation_errors







