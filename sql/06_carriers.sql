-- Carrier scorecard over the whole window.
SELECT f.carrier,
       COUNT(*) AS scheduled,
       AVG(cancelled::INT) AS cancel_rate,
       AVG(1 - arr_del15) FILTER (WHERE operated) AS on_time_rate,
       AVG(arr_delay_min) FILTER (WHERE operated) AS arr_delay_min_per_flight,
       SUM(arr_delay_min) FILTER (WHERE operated) AS arr_delay_minutes,
       SUM(GREATEST(dep_delay, 0)) FILTER (WHERE operated) AS dep_delay_minutes,
       SUM(GREATEST(arr_delay - GREATEST(dep_delay, 0), 0)) FILTER (WHERE operated) AS extra_block_minutes,
       SUM(carrier_delay) AS carrier_minutes, SUM(weather_delay) AS weather_minutes, SUM(nas_delay) AS nas_minutes,
       SUM(security_delay) AS security_minutes, SUM(late_aircraft_delay) AS late_aircraft_minutes,
       COUNT(DISTINCT tail) AS aircraft,
       COUNT(DISTINCT year_month) AS months_reported
FROM flights f
GROUP BY f.carrier
ORDER BY scheduled DESC
