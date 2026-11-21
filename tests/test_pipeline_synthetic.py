"""Warehouse, rotation linking and propagation on synthetic BTS-shaped data (see src/synthetic.py)."""
import pytest

from src import config, data, synthetic

MONTHS = [(2025, 10), (2025, 11)]


@pytest.fixture(scope="module")
def warehouse(tmp_path_factory):
    raw = tmp_path_factory.mktemp("raw")
    synthetic.write(raw, MONTHS, days=10)
    mp = pytest.MonkeyPatch()
    for name, value in {"RAW_DIR": raw, "BTS_DIR": raw / "bts", "AIRPORTS_CSV": raw / "airports.csv",
                        "PARQUET_DIR": raw / "parquet", "DB_PATH": raw / "test.duckdb", "MONTHS": MONTHS,
                        "START": "2025-10-01", "END": "2025-11-30"}.items():
        mp.setattr(config, name, value)
    checks = data.build_warehouse()
    yield checks
    mp.undo()


def test_hard_rules_pass(warehouse):
    assert (warehouse[warehouse.severity == "hard"].failures == 0).all()


def test_rotations_link_consecutive_legs(warehouse):
    counts = data.row_counts()
    assert counts["flights"] == 2 * 10 * 30 * 4
    turns = data.query("SELECT sched_turn, COUNT(*) AS n FROM turns GROUP BY 1 ORDER BY 1")
    assert set(turns.sched_turn) <= {30, 40, 45, 60, 75, 90}
    # three turns per aircraft-day, minus turns next to a cancelled leg
    assert 0.9 * 2 * 10 * 30 * 3 <= turns.n.sum() <= 2 * 10 * 30 * 3


def test_minimum_turn_and_propagation_are_recovered(warehouse):
    mt = data.query("SELECT * FROM min_turn").set_index("carrier")
    assert abs(mt.loc["XX", "min_turn"] - synthetic.TRUE_MIN_TURN) <= 6
    chk = data.query("16_propagation_check.sql").iloc[0]
    assert chk.correlation > 0.8


def test_buffer_scenarios_are_monotonic_and_bounded(warehouse):
    b = data.query("05_buffer_scenarios.sql")
    allb = b[(b.carrier == "All") & (b.time_window == "All day") & (b.threshold == 60)].sort_values("buffer")
    assert (allb.minutes_avoided.diff().dropna() >= 0).all()
    assert (b.minutes_avoided <= b.propagated_now + 1e-9).all()
