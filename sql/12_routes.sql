-- Routes ranked by total arrival delay minutes (routes with at least 2,000 scheduled flights).
SELECT origin, dest, origin || '-' || dest AS route,
       COUNT(*) AS scheduled,
       AVG(cancelled::INT) AS cancel_rate,
       AVG(arr_del15) FILTER (WHERE operated) AS arr_delay15_rate,
       SUM(arr_delay_min) FILTER (WHERE operated) AS arr_delay_minutes,
       AVG(arr_delay_min) FILTER (WHERE operated) AS arr_delay_min_per_flight,
       COUNT(DISTINCT carrier) AS carriers
FROM flights
GROUP BY origin, dest
HAVING COUNT(*) >= 2000
ORDER BY arr_delay_minutes DESC
LIMIT 50
