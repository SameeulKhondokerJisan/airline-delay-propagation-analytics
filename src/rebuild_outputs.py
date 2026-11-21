"""Rebuild the Tableau workbook, Excel model and README from the saved result tables, without rerunning the
pipeline (used after a layout change).

Usage:
    python -m src.rebuild_outputs
"""
from __future__ import annotations

import json

import pandas as pd

from src import config, excel_model, report, tableau_workbook


def main() -> None:
    t = lambda name: pd.read_csv(config.TABLES / f"{name}.csv")  # noqa: E731
    results = json.loads(config.RESULTS_JSON.read_text())
    sc, buffers, ct = t("carrier_scorecard"), t("buffer_scenarios"), t("carrier_turns")
    results["tableau"] = tableau_workbook.build(t("airports"), sc, t("hourly"), t("monthly_causes"), t("turn_profile"),
                                                buffers, t("shutdown_weekly"), ct)
    results["excel"] = excel_model.build(results, sc, buffers, ct)
    report.render(results)
    config.RESULTS_JSON.write_text(json.dumps(results, indent=2, default=str))
    print("rebuilt", results["tableau"], results["excel"])


if __name__ == "__main__":
    main()
