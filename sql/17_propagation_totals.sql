-- Network totals of the propagation model.
SELECT COUNT(*) AS turns,
       AVG((prev_arr_delay >= 15)::INT) AS share_inbound_late,
       AVG((propagated > 0)::INT) AS share_with_propagated,
       AVG((propagated >= 15)::INT) AS share_propagated_15,
       SUM(propagated) AS propagated_minutes,
       SUM(GREATEST(dep_delay, 0)) AS departure_delay_minutes,
       SUM(propagated) / SUM(GREATEST(dep_delay, 0)) AS propagated_share_of_departure_delay,
       MEDIAN(sched_turn) AS median_sched_turn,
       AVG((sched_turn <= 45)::INT) AS share_turns_45_or_less,
       SUM(propagated) FILTER (WHERE sched_turn <= 45) / SUM(propagated) AS propagated_share_from_turns_45_or_less
FROM propagation
