"""The recalculated Excel model reproduces the pipeline's numbers (skipped until the workbook has cached values)."""
import json

import pytest
from openpyxl import load_workbook

from src import config, excel_model

pytestmark = pytest.mark.skipif(not config.EXCEL_PATH.exists() or not config.RESULTS_JSON.exists(),
                                reason="run `make pipeline` first")


def test_workbook_matches_pipeline():
    wb = load_workbook(config.EXCEL_PATH, data_only=True)
    if wb["Buffer scenario"]["B5"].value is None:
        pytest.skip("workbook not recalculated yet (open and save it in Excel, or run LibreOffice recalc)")
    expected = excel_model.expected_totals(json.loads(config.RESULTS_JSON.read_text()))
    for ref, value in expected.items():
        sheet, cell = ref.split("!")
        assert wb[sheet][cell].value == pytest.approx(value, rel=1e-9), ref
