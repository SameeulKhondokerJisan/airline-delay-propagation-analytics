-- Daily network totals (used for the shutdown comparison and the daily chart).
SELECT flight_date, dow,
       COUNT(*) AS scheduled,
       SUM(cancelled::INT) AS cancelled,
       COUNT(*) FILTER (WHERE cancel_code = 'C') AS cancelled_nas,
       SUM(operated::INT) AS operated,
       SUM(arr_del15) FILTER (WHERE operated) AS delayed15,
       SUM(arr_delay_min) FILTER (WHERE operated) AS arr_delay_minutes,
       SUM(carrier_delay) AS carrier_minutes, SUM(weather_delay) AS weather_minutes, SUM(nas_delay) AS nas_minutes,
       SUM(security_delay) AS security_minutes, SUM(late_aircraft_delay) AS late_aircraft_minutes
FROM flights
GROUP BY flight_date, dow
ORDER BY flight_date
