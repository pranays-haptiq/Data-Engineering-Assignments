{{ config(materialized='table') }}

select
    b.bike_id,
    b.bike_model,
    sum(t.trip_cost)                              as total_cost,
    sum(t.trip_duration_seconds) / 60             as total_minutes
from {{ ref('stg_bikes') }} b
join {{ source('greenwheel', 'raw_trips') }} t
    on b.bike_id = t.bike_id
group by b.bike_id, b.bike_model
