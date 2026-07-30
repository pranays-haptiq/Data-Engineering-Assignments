{{ config(materialized='view') }}

select
    user_id,
    UPPER(user_name) as user_name,
    LOWER(email)     as email,
    created_at
from {{ source('greenwheel', 'raw_users') }}
