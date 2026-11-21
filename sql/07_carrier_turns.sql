-- Carrier turn statistics: scheduled ground time, minimum turn, share of departures with propagated delay.
SELECT p.carrier,
       COUNT(*) AS turns,
       MEDIAN(sched_turn) AS median_sched_turn,
       ANY_VALUE(min_turn) AS min_turn,
       AVG((slack <= 15)::INT) AS share_slack_15_or_less,
       AVG((propagated > 0)::INT) AS share_with_propagated,
       SUM(propagated) AS propagated_minutes,
       SUM(own_departure_delay) AS own_departure_minutes
FROM propagation p
GROUP BY p.carrier
ORDER BY turns DESC
