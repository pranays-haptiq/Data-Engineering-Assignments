






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and total_events >= 1
)
 as expression


    from "postgres"."public"."fct_dividend_performance"
    

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







