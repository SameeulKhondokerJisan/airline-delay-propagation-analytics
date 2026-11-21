-- Delay build-up through the day, by scheduled departure hour (local time).
SELECT dep_hour,
       COUNT(*) AS scheduled,
       AVG(dep_del15) FILTER (WHERE NOT cancelled) AS dep_delay15_rate,
       AVG(arr_del15) FILTER (WHERE operated) AS arr_delay15_rate,
       AVG(arr_delay_min) FILTER (WHERE operated) AS arr_delay_min_per_flight,
       SUM(late_aircraft_delay) / NULLIF(SUM(carrier_delay + weather_delay + nas_delay + security_delay
                                             + late_aircraft_delay), 0) AS late_aircraft_share,
       AVG(cancelled::INT) AS cancel_rate
FROM flights
GROUP BY dep_hour
ORDER BY dep_hour
