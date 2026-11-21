-- Departures from large airports during the shutdown (1 Oct - 12 Nov 2025) against the same weekdays a year
-- earlier (364 days back).
WITH w AS (
    SELECT origin, flight_date >= DATE '{shutdown_start}' AS this_year, cancelled, dep_del15, nas_delay
    FROM flights
    WHERE flight_date BETWEEN DATE '{shutdown_start}' AND DATE '{shutdown_end}'
       OR flight_date BETWEEN DATE '{shutdown_start}' - 364 AND DATE '{shutdown_end}' - 364
)
SELECT origin AS airport,
       COUNT(*) FILTER (WHERE this_year) AS departures_2025,
       COUNT(*) FILTER (WHERE NOT this_year) AS departures_2024,
       AVG(cancelled::INT) FILTER (WHERE this_year) AS cancel_rate_2025,
       AVG(cancelled::INT) FILTER (WHERE NOT this_year) AS cancel_rate_2024,
       AVG(dep_del15) FILTER (WHERE this_year AND NOT cancelled) AS dep_delay15_2025,
       AVG(dep_del15) FILTER (WHERE NOT this_year AND NOT cancelled) AS dep_delay15_2024,
       SUM(nas_delay) FILTER (WHERE this_year) / COUNT(*) FILTER (WHERE this_year) AS nas_min_per_dep_2025,
       SUM(nas_delay) FILTER (WHERE NOT this_year) / COUNT(*) FILTER (WHERE NOT this_year) AS nas_min_per_dep_2024
FROM w
GROUP BY origin
HAVING COUNT(*) FILTER (WHERE this_year) >= 5000
ORDER BY departures_2025 DESC
