-- How scheduled ground time absorbs an inbound delay: outcomes by 5-minute scheduled-turn bin.
SELECT LEAST(sched_turn // 5 * 5, 180) AS sched_turn_bin,
       COUNT(*) AS turns,
       AVG((prev_arr_delay >= 15)::INT) AS share_inbound_late,
       AVG(GREATEST(dep_delay, 0)) FILTER (WHERE prev_arr_delay >= 15) AS mean_dep_delay_if_inbound_late,
       AVG((dep_delay >= 15)::INT) FILTER (WHERE prev_arr_delay >= 15) AS share_departs_late_if_inbound_late,
       AVG((dep_delay >= 15)::INT) FILTER (WHERE prev_arr_delay < 15) AS share_departs_late_if_inbound_on_time,
       SUM(propagated) / NULLIF(SUM(GREATEST(prev_arr_delay, 0)), 0) AS pass_through,
       AVG(propagated) AS mean_propagated
FROM propagation
WHERE sched_turn >= 25
GROUP BY 1
ORDER BY 1
