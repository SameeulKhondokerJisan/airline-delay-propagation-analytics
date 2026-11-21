-- Delay minutes by cause and month (minutes of arrival delay on flights 15+ minutes late, as reported by carriers).
SELECT year_month,
       COUNT(*) AS scheduled,
       AVG(cancelled::INT) AS cancel_rate,
       AVG(1 - arr_del15) FILTER (WHERE operated) AS on_time_rate,
       SUM(carrier_delay) AS carrier_minutes, SUM(weather_delay) AS weather_minutes, SUM(nas_delay) AS nas_minutes,
       SUM(security_delay) AS security_minutes, SUM(late_aircraft_delay) AS late_aircraft_minutes
FROM flights
GROUP BY year_month
ORDER BY year_month
