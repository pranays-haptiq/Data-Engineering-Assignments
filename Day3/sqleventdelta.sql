WITH RankedEvents AS (
    SELECT 
        event_type,
        value AS latest_value,
        LEAD(value) OVER (PARTITION BY event_type ORDER BY time DESC) AS second_latest_value,
        ROW_NUMBER() OVER (PARTITION BY event_type ORDER BY time DESC) AS rn
    FROM events
)
SELECT 
    event_type,
    (latest_value - second_latest_value) AS value
FROM RankedEvents
WHERE rn = 1 
  AND second_latest_value IS NOT NULL
ORDER BY event_type ASC;