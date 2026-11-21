-- Carrier x day counts for the day-level bootstrap of on-time rates.
SELECT carrier, flight_date,
       COUNT(*) AS scheduled,
       SUM(cancelled::INT) AS cancelled,
       SUM(operated::INT) AS operated,
       SUM((1 - arr_del15)) FILTER (WHERE operated) AS on_time
FROM flights
GROUP BY carrier, flight_date
