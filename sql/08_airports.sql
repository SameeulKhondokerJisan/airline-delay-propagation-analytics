-- Departure performance by origin airport (airports with at least {min_airport_flights} scheduled departures).
SELECT f.origin AS airport, a.airport_name, a.municipality, a.lat, a.lon,
       ANY_VALUE(f.origin_state) AS state,
       COUNT(*) AS departures,
       AVG(cancelled::INT) AS cancel_rate,
       AVG(dep_del15) FILTER (WHERE NOT cancelled) AS dep_delay15_rate,
       AVG(GREATEST(dep_delay, 0)) FILTER (WHERE NOT cancelled) AS dep_delay_min_per_flight,
       AVG(taxi_out) FILTER (WHERE NOT cancelled) AS mean_taxi_out,
       SUM(nas_delay) / COUNT(*) AS nas_minutes_per_departure,
       SUM(late_aircraft_delay) / NULLIF(SUM(carrier_delay + weather_delay + nas_delay + security_delay
                                             + late_aircraft_delay), 0) AS late_aircraft_share
FROM flights f LEFT JOIN airports a ON a.airport = f.origin
GROUP BY f.origin, a.airport_name, a.municipality, a.lat, a.lon
HAVING COUNT(*) >= {min_airport_flights}
ORDER BY departures DESC
