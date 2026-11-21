# Methodology

## Data and scope
BTS Reporting Carrier On-Time Performance, October 2024 to September 2026: every scheduled domestic flight of the
carriers that report to the Department of Transportation (14 to 15 carriers depending on the month). A flight is
*operated* when it was neither cancelled nor diverted and has an arrival time. On-time means arriving less than
15 minutes after schedule, the DOT definition. Every rule and its row count is in `data_quality_log.md`.

**Times.** Scheduled times are local hhmm at each airport; 2400 is read as minute 0. Minutes are counted from
1 October 2024 on the local clock of the airport concerned: departure = day x 1440 + scheduled departure minute;
arrival = day x 1440 + scheduled arrival minute + 1440 x round((departure minute + scheduled block time - arrival
minute) / 1440), which adds a day for overnight arrivals and works for time-zone differences under 12 hours. A
departure and the previous arrival of the same aircraft happen at the same airport, so they are on the same clock
and can be subtracted directly.

## Delay causes
Carriers assign every minute of arrival delay on flights 15+ minutes late to five causes: carrier (crew,
maintenance, cleaning, fuelling), extreme weather, National Aviation System (air traffic control, airport
operations, heavy traffic, non-extreme weather), security, and late-arriving aircraft (delay carried from the
aircraft's previous flight). **Delay multiplier** = all delay minutes / delay minutes from the four root causes,
the extra minutes created by each minute of original delay as it moves through rotations.

## Aircraft rotations and propagated delay
`sql/03_rotations.sql` orders each aircraft's operated flights (carrier and tail number) by scheduled departure
with a window function and links each flight to the previous one when the previous flight landed where this one
departs and the scheduled ground time is 10 to 240 minutes. Linked pairs are *turns*.

* **Minimum turn time** per carrier: the 5th percentile of actual ground time on turns where the inbound flight
  arrived 15+ minutes late and the outbound still left 15+ minutes late (the crew turned the aircraft as fast as it
  could). Fleet mix differs within a carrier, so this is a carrier-wide approximation.
* **Slack** = scheduled turn - minimum turn, floored at zero.
* **Propagated delay** on the outbound departure = max(0, inbound arrival delay - slack), capped at the outbound
  departure delay. The rest of the departure delay is the outbound flight's own delay. This is the decomposition
  used by AhmadBeygi, Cohn, Guan and Belobaba (2008), "Analysis of the potential for delay propagation in
  passenger airline networks", Journal of Air Transport Management 14(5).
* **Check:** on outbound flights that arrived 15+ minutes late, the estimate is compared with the late-aircraft
  minutes the carrier reported (`sql/16_propagation_check.sql`); results are in `results.json` and the README.

## Turn-buffer scenarios
For each carrier, turn threshold (45, 60, 75, 90 minutes) and buffer (5 to 30 minutes), every turn scheduled at or
below the threshold gets the buffer: new slack = max(0, scheduled turn + buffer - minimum turn), and propagated
delay is recomputed flight by flight with the actual inbound delay. Minutes avoided = propagated now - propagated
after. This is first-order: it counts the next departure only, not the later flights that would also leave closer
to schedule, so it understates the benefit; it also assumes the extra minutes do not change crew or gate plans.
In Excel the avoided minutes are priced at the gate-minute cost (crew, ownership and other, from A4A's 2025 cost
per block minute) plus passenger time, and the buffer costs turns x minutes x a cost per minute of added
ground time (default: ownership plus other).

## Carrier scorecard
On-time arrival rate per carrier with 95% intervals from a day-level bootstrap: 1,000 resamples of the 730 days,
the same days for every carrier, so weather and congestion shared by flights on the same day are kept together.
Carriers that did not report in all 24 months are listed in the tables but left out of the ranking charts.

## The 2025 shutdown
The federal government shutdown ran from 1 October to 12 November 2025 (43 days). The FAA ordered airlines to cut
flights at 40 high-traffic airports from 7 November (4%, raised to 6%, then 3% on 14 November) until 6 am on
17 November. For every day from 1 October to 31 December 2025, each metric is compared with the same weekday
364 days earlier, and the year-over-year differences are regressed on three period indicators (shutdown before
the cuts, shutdown with cuts, cuts after the shutdown ended) with 17 November - 31 December as the baseline.
Newey-West standard errors with 7 lags allow for correlation between nearby days. Metrics: NAS delay minutes per
scheduled flight, cancellation rate, cancellations coded NAS, on-time rate and arrival delay minutes per flight.
The comparison controls for season and weekday but not for weather differences between the two years.

## Disruption-risk model
Target: the flight was cancelled, diverted or arrived 15+ minutes late. Features known when the schedule is
published: carrier, origin, destination (categorical), scheduled departure and arrival hour, weekday, month,
distance, scheduled block time, the planned ground time before the flight (previous scheduled flight of the same
tail, cancelled flights included) and the planned leg number of the day. LightGBM, binary objective, 400 rounds,
learning rate 0.05, 127 leaves, fixed seed; trained on a 5-million-row random sample of October 2024 - March 2026
and tested on every flight of April - September 2026. Baseline: logistic regression on carrier, departure hour and
month. Reported: AUC, Brier score against a constant forecast, log loss, calibration in 20 bins and disruption
rate by risk decile. Hyperparameters were fixed before testing.

## Limits
* Only reporting carriers are included; regional flights are reported by the regional carrier that operates them.
* Cause coding is done by carriers and is not audited flight by flight.
* The minimum turn is carrier-wide; aircraft types with shorter turns are floored at zero slack.
* Delay costs use industry averages per minute, not each carrier's own costs; cancellations are not priced.
