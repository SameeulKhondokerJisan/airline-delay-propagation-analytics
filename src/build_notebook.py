"""Create notebooks/airline_delay_propagation.ipynb (executed by `make notebook`)."""
import nbformat as nbf

from src import config

CELLS = [
    ("md", "# US airline delays: where they start, how they spread, what they cost\nWalk-through of the analysis "
           "behind the README. SQL runs live against the DuckDB warehouse built by `src/run_pipeline.py`; the "
           "bootstrap and the risk model are read from `reports/`."),
    ("code", "import os, sys, json, pathlib\nROOT = pathlib.Path.cwd().parent if pathlib.Path.cwd().name == 'notebooks' "
             "else pathlib.Path.cwd()\nos.chdir(ROOT); sys.path.insert(0, str(ROOT))\nimport pandas as pd\n"
             "from IPython.display import Image, Markdown, display\nfrom src import config, data\n"
             "pd.set_option('display.float_format', lambda x: f'{x:,.4f}')\npd.set_option('display.width', 160)\n"
             "results = json.loads(config.RESULTS_JSON.read_text())\nT = lambda name: pd.read_csv(f'reports/tables/{name}.csv')"),
    ("md", "## 1. Data quality and scale"),
    ("code", "display(T('quality_checks'))\ndisplay(data.row_counts())\nresults['network']"),
    ("code", "display(T('monthly_causes'))\ndisplay(Image(filename='reports/figures/01_monthly_on_time.png'))"),
    ("md", "## 2. Causes of delay\nCarriers code every arrival delay of 15+ minutes into five causes. Late-arriving "
           "aircraft is delay carried from an earlier flight of the same aircraft."),
    ("code", "display(pd.Series(results['causes']['shares']).sort_values(ascending=False))\n"
             "print('delay multiplier:', round(results['causes']['delay_multiplier'], 3))\n"
             "display(Image(filename='reports/figures/02_delay_causes.png'))"),
    ("code", "display(T('hourly'))\ndisplay(Image(filename='reports/figures/03_delay_by_hour.png'))"),
    ("md", "## 3. Aircraft rotations and delay propagation\n`sql/03_rotations.sql` links each flight to the previous "
           "flight of the same aircraft with a window function, then estimates how much of each departure delay "
           "was carried in from the inbound flight."),
    ("code", "data.query('SELECT carrier, tail, origin, dest, sched_turn, actual_turn, prev_arr_delay, dep_delay, slack, "
             "propagated FROM propagation WHERE prev_arr_delay > 30 LIMIT 8')"),
    ("code", "display(T('min_turn'))\ndisplay(data.query('16_propagation_check.sql'))\n"
             "display(data.query('17_propagation_totals.sql'))"),
    ("code", "display(Image(filename='reports/figures/04_turn_propagation.png'))\ndisplay(T('carrier_turns'))"),
    ("md", "## 4. Carrier scorecard\nOn-time arrival rates with 95% intervals from resampling whole days."),
    ("code", "sc = T('carrier_scorecard')\ndisplay(sc[['carrier_name', 'scheduled', 'on_time_rate', 'on_time_ci_low', "
             "'on_time_ci_high', 'cancel_rate', 'late_aircraft_share', 'delay_multiplier', 'full_window']])\n"
             "display(Image(filename='reports/figures/05_carrier_on_time.png'))"),
    ("md", "## 5. The 2025 shutdown\nDaily metrics against the same weekday 364 days earlier, regressed on the shutdown "
           "and flight-cut periods with Newey-West errors."),
    ("code", "display(T('shutdown_period_means'))\ndisplay(T('shutdown_effects'))\n"
             "display(Image(filename='reports/figures/06_shutdown_weekly.png'))"),
    ("code", "T('shutdown_airports').sort_values('nas_change', ascending=False).head(10)"),
    ("md", "## 6. Disruption-risk model\nLightGBM on schedule-time features, trained on Oct 2024 - Mar 2026 and "
           "tested on Apr - Sep 2026."),
    ("code", "m = results['model']\n{k: m[k] for k in ('train_rows', 'test_rows', 'base_rate_test', 'auc', 'auc_baseline', "
             "'brier', 'brier_climatology', 'top_decile_rate', 'top_decile_lift')}"),
    ("code", "display(T('model_importance').head(10))\ndisplay(Image(filename='reports/figures/08_model_lift_calibration.png'))"),
    ("md", "## 7. Turn-buffer scenarios"),
    ("code", "b = T('buffer_scenarios')\ndisplay(b[b.carrier == 'All'])\n"
             "display(Image(filename='reports/figures/09_buffer_scenarios.png'))"),
    ("md", "## 8. Memo"),
    ("code", "display(Markdown(open('reports/memo.md').read()))"),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if k == "md" else nbf.v4.new_code_cell(s) for k, s in CELLS]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    (config.ROOT / "notebooks").mkdir(exist_ok=True)
    nbf.write(nb, config.ROOT / "notebooks" / "airline_delay_propagation.ipynb")


if __name__ == "__main__":
    main()
