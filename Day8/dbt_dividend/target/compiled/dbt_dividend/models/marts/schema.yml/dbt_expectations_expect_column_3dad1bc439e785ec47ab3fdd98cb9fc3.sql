






    with grouped_expression as (
    select
        
        
    
  
( 1=1 and avg_dividend > 0
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







