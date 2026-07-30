






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and dividend_amount > 0
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







