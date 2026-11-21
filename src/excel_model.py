"""Build excel/delay_cost_turn_buffer_model.xlsx.

Two decisions in one workbook: what delays cost each carrier (airline operating cost plus passenger time), and
whether adding minutes to short scheduled turns pays for itself. Every calculated cell is a formula over the
Inputs sheet and the pasted pipeline tables, so an analyst can change the cost rates, the carrier, the turn
threshold or the buffer and see the result. With the default inputs the workbook reproduces the pipeline's
numbers (checked by tests/test_excel.py after recalculation).

Colour code: blue = typed input or pasted data, black = formula, green = link to another sheet,
yellow fill = assumption to review.
"""
from __future__ import annotations

import pandas as pd
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

from src import config

ARIAL = "Arial"
BLUE, BLACK, GREEN, WHITE = "0000FF", "000000", "008000", "FFFFFF"
HEADER = PatternFill("solid", fgColor="1F3864")
YELLOW = PatternFill("solid", fgColor="FFFF00")
GOOD = PatternFill("solid", fgColor="C6EFCE")
BAD = PatternFill("solid", fgColor="F8CBAD")
THIN = Side(style="thin", color="BFBFBF")
BOX = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
USD = '"$"#,##0;("$"#,##0);"-"'
USD2 = '"$"#,##0.00;("$"#,##0.00);"-"'
PCT = '0.0%;(0.0%);"-"'
NUM = '#,##0;(#,##0);"-"'
NUM1 = '#,##0.0;(#,##0.0);"-"'
SRC = ("Source: BTS Reporting Carrier On-Time Performance, Oct 2024 - Sep 2026; cost rates from Airlines for America "
       "(2025 cost per block minute, DOT Form 41). Built by src/excel_model.py from reports/results.json.")
DEFAULT_CARRIER, DEFAULT_WINDOW, DEFAULT_THRESHOLD, DEFAULT_BUFFER = "All", "All day", 60, 15
WINDOWS = ["All day", "Departures from 15:00"]


def _c(ws, ref, value, color=BLACK, fmt=None, bold=False, fill=None, note=None, italic=False, size=10):
    cell = ws[ref]
    cell.value = value
    cell.font = Font(name=ARIAL, color=color, bold=bold, italic=italic, size=size)
    if fmt:
        cell.number_format = fmt
    if fill:
        cell.fill = fill
    if note:
        cell.comment = Comment(note, "pipeline")
    return cell


def _head(ws, row, labels, col=1):
    for i, text in enumerate(labels):
        cell = ws.cell(row=row, column=col + i, value=text)
        cell.font = Font(name=ARIAL, color=WHITE, bold=True)
        cell.fill = HEADER
        cell.border = BOX
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _widths(ws, widths: dict[str, float]) -> None:
    for col, w in widths.items():
        ws.column_dimensions[col].width = w


def build(results: dict, carriers: pd.DataFrame, buffers: pd.DataFrame, carrier_turns: pd.DataFrame) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    _c(ws, "A1", "US airline delays: cost model and turn-buffer business case", bold=True, size=14)
    _c(ws, "A2", "What delays cost each carrier, and whether extra minutes on short turns pay for themselves",
       italic=True)
    for i, text in enumerate([
        "Inputs: cost per block minute by component (A4A, 2025), which components accrue while an aircraft waits at "
        "the gate, passengers per departure, value of passenger time, and the buffer scenario (yellow cells).",
        "Carrier delay cost: 24 months of delay minutes per carrier (blue) priced with the input rates. Departure "
        "delay minutes are priced at the gate rate; extra taxi and airborne minutes at the full block rate; "
        "every arrival delay minute costs passengers' time.",
        "Buffer scenario: propagated delay avoided on the next departure when a carrier adds minutes to every "
        "turn scheduled at or below a threshold (computed flight by flight in sql/05_buffer_scenarios.sql), against "
        "the cost of the extra aircraft time.",
        "Buffer grid: net benefit for the chosen carrier across every threshold and buffer size.",
        "Method: propagated delay = inbound arrival delay - (scheduled turn - carrier minimum turn), floored at zero "
        "and capped at the outbound departure delay. Avoided minutes are first-order: they ignore the further "
        "delay the next flights would also avoid, so the benefit is a lower bound.",
        "Annual figures scale the 24-month totals by 12 / 24.",
        "Colour code: blue = input or pasted data; black = formula; green = link to another sheet; yellow fill = "
        "assumption to review.",
        SRC,
    ], start=4):
        _c(ws, f"A{i}", text)
    ws.column_dimensions["A"].width = 130

    # ------------------------------------------------------------------ Inputs
    inp = wb.create_sheet("Inputs")
    _c(inp, "A1", "Inputs", bold=True, size=14)
    _c(inp, "A2", "Edit the yellow cells; everything else recalculates.", italic=True)
    _head(inp, 4, ["Cost per block minute (2025, $)", "Value", "Accrues at the gate?", "Note"])
    comps = list(config.COST_PER_BLOCK_MINUTE.items())
    for i, (name, value) in enumerate(comps, start=5):
        _c(inp, f"A{i}", name)
        _c(inp, f"B{i}", value, BLUE, USD2, fill=YELLOW)
        _c(inp, f"C{i}", "Yes" if name in config.GATE_COMPONENTS else "No", BLUE, fill=YELLOW)
        _c(inp, f"D{i}", "Airlines for America, U.S. Passenger Carrier Delay Costs (2025, DOT Form 41)")
    last = 4 + len(comps)
    rows = [
        (last + 1, "Full block-minute cost ($)", f"=SUM(B5:B{last})", USD2, None, "Taxi plus airborne minute"),
        (last + 2, "Gate-minute cost ($)", f'=SUMIFS(B5:B{last},C5:C{last},"Yes")', USD2, None,
         "Components marked Yes above: crew, ownership and other by default (no fuel burn at the gate)"),
        (last + 3, "Passengers per departure", round(config.PASSENGERS_PER_DEPARTURE, 1), "0.0", YELLOW,
         "BTS national summary, 12 months to Jan 2026: 840 million passengers / 8,759 thousand departures"),
        (last + 4, "Value of passenger time ($ per hour)", config.PASSENGER_VALUE_OF_TIME, USD2, YELLOW,
         "FAA-recommended value quoted by A4A"),
        (last + 5, "Passenger cost per delay minute ($)", f"=B{last + 3}*B{last + 4}/60", USD2, None, ""),
        (last + 7, "Buffer scenario: carrier", DEFAULT_CARRIER, None, YELLOW, "All or a carrier code"),
        (last + 8, "Buffer scenario: turns scheduled at or below (minutes)", DEFAULT_THRESHOLD, "0", YELLOW,
         ", ".join(map(str, config.TURN_THRESHOLDS))),
        (last + 9, "Buffer scenario: minutes added per turn", DEFAULT_BUFFER, "0", YELLOW,
         ", ".join(map(str, config.BUFFER_MINUTES))),
        (last + 10, "Cost per minute of added ground time ($)", "=B8+B9", USD2, YELLOW,
         "Default: aircraft ownership + other. Replace with your own aircraft opportunity cost."),
        (last + 11, "Months in the data", len(config.MONTHS), "0", None, "Annual = 24-month total x 12 / months"),
        (last + 12, "Buffer scenario: which turns", DEFAULT_WINDOW, None, YELLOW,
         "All day, or only turns before departures from 15:00 local time (when inbound delays are common)"),
    ]
    for r, label, value, fmt, fill, note in rows:
        _c(inp, f"A{r}", label)
        color = BLUE if not (isinstance(value, str) and value.startswith("=")) else BLACK
        _c(inp, f"B{r}", value, color, fmt, fill=fill)
        _c(inp, f"D{r}", note)
    refs = {"block": f"Inputs!$B${last + 1}", "gate": f"Inputs!$B${last + 2}", "pax": f"Inputs!$B${last + 5}",
            "carrier": f"Inputs!$B${last + 7}", "threshold": f"Inputs!$B${last + 8}", "buffer": f"Inputs!$B${last + 9}",
            "ground": f"Inputs!$B${last + 10}", "months": f"Inputs!$B${last + 11}", "window": f"Inputs!$B${last + 12}"}
    carrier_codes = ["All"] + list(carriers.carrier)
    for ref, options in ((f"B{last + 7}", ",".join(carrier_codes)), (f"B{last + 8}", ",".join(map(str, config.TURN_THRESHOLDS))),
                         (f"B{last + 9}", ",".join(map(str, config.BUFFER_MINUTES))), (f"B{last + 12}", ",".join(WINDOWS))):
        dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=False)
        inp.add_data_validation(dv)
        dv.add(ref)
    for i in range(5, last + 1):
        dv = DataValidation(type="list", formula1='"Yes,No"', allow_blank=False)
        inp.add_data_validation(dv)
        dv.add(f"C{i}")
    _widths(inp, {"A": 52, "B": 14, "C": 18, "D": 95})

    # ------------------------------------------------------------------ Carrier delay cost
    cs = wb.create_sheet("Carrier delay cost")
    _c(cs, "A1", "Delay cost by carrier, Oct 2024 - Sep 2026", bold=True, size=14)
    _c(cs, "A2", SRC, italic=True)
    _head(cs, 4, ["Carrier", "Name", "Scheduled flights", "Departure delay minutes", "Extra taxi and airborne minutes",
                  "Arrival delay minutes", "Airline cost at the gate ($)", "Airline cost in the air ($)",
                  "Passenger time cost ($)", "Total cost ($)", "Cost per scheduled flight ($)", "Annual total ($)"])
    for i, r in enumerate(carriers.itertuples(), start=5):
        _c(cs, f"A{i}", r.carrier, BLUE)
        _c(cs, f"B{i}", r.carrier_name, BLUE)
        _c(cs, f"C{i}", int(r.scheduled), BLUE, NUM)
        _c(cs, f"D{i}", float(r.dep_delay_minutes), BLUE, NUM)
        _c(cs, f"E{i}", float(r.extra_block_minutes), BLUE, NUM)
        _c(cs, f"F{i}", float(r.arr_delay_minutes), BLUE, NUM)
        _c(cs, f"G{i}", f"=D{i}*{refs['gate']}", fmt=USD)
        _c(cs, f"H{i}", f"=E{i}*{refs['block']}", fmt=USD)
        _c(cs, f"I{i}", f"=F{i}*{refs['pax']}", fmt=USD)
        _c(cs, f"J{i}", f"=G{i}+H{i}+I{i}", fmt=USD)
        _c(cs, f"K{i}", f"=IF(C{i}=0,0,J{i}/C{i})", fmt=USD2)
        _c(cs, f"L{i}", f"=J{i}*12/{refs['months']}", fmt=USD)
    t = 5 + len(carriers)
    _c(cs, f"A{t}", "Total", bold=True)
    for col in "CDEFGHIJL":
        _c(cs, f"{col}{t}", f"=SUM({col}5:{col}{t - 1})", fmt=NUM if col in "CDEF" else USD, bold=True)
    _c(cs, f"K{t}", f"=IF(C{t}=0,0,J{t}/C{t})", fmt=USD2, bold=True)
    _widths(cs, {"A": 9, "B": 22, **{c: 16 for c in "CDEFGHIJKL"}})
    cs.freeze_panes = "C5"
    carrier_total_row = t

    # ------------------------------------------------------------------ Buffer data
    bd = wb.create_sheet("Buffer data")
    _c(bd, "A1", "Propagated delay avoided by extra turn time (from sql/05_buffer_scenarios.sql)", bold=True, size=14)
    _c(bd, "A2", "Minutes are summed over 24 months of linked aircraft turns.", italic=True)
    _head(bd, 4, ["Carrier", "Threshold (min)", "Buffer (min)", "Turns buffered", "Propagated minutes now",
                  "Propagated minutes after", "Minutes avoided", "Which turns"])
    b = buffers.sort_values(["carrier", "time_window", "threshold", "buffer"]).reset_index(drop=True)
    for i, r in enumerate(b.itertuples(), start=5):
        for j, v in enumerate([r.carrier, int(r.threshold), int(r.buffer), int(r.turns_buffered), float(r.propagated_now),
                               float(r.propagated_after), float(r.minutes_avoided), r.time_window]):
            cell = bd.cell(row=i, column=1 + j, value=v)
            cell.font = Font(name=ARIAL, color=BLUE)
            if 3 <= j <= 6:
                cell.number_format = NUM
    bl = 4 + len(b)
    rng = lambda col: f"'Buffer data'!${col}$5:${col}${bl}"  # noqa: E731
    _widths(bd, {"A": 9, **{c: 16 for c in "BCDEFG"}, "H": 22})

    # ------------------------------------------------------------------ Buffer scenario
    sc = wb.create_sheet("Buffer scenario", 2)
    _c(sc, "A1", "Turn-buffer business case", bold=True, size=14)
    _c(sc, "A2", '="Carrier "&' + refs["carrier"] + '&", "&' + refs["window"] + '&", turns scheduled at or below "&'
       + refs["threshold"] + '&" min, plus "&' + refs["buffer"] + '&" min each"', italic=True)
    _head(sc, 4, ["Line", "24 months", "Per year", "Note"])
    lines = [
        ("Turns that get the buffer", f"=SUMIFS({rng('D')},{rng('A')},{refs['carrier']},{rng('H')},{refs['window']},{rng('B')},{refs['threshold']},"
                                      f"{rng('C')},{refs['buffer']})", NUM, "Linked aircraft turns at or below the threshold"),
        ("Propagated delay now (minutes)", f"=SUMIFS({rng('E')},{rng('A')},{refs['carrier']},{rng('H')},{refs['window']},{rng('B')},{refs['threshold']},"
                                           f"{rng('C')},{refs['buffer']})", NUM, "On those turns"),
        ("Propagated delay avoided (minutes)", f"=SUMIFS({rng('G')},{rng('A')},{refs['carrier']},{rng('H')},{refs['window']},{rng('B')},"
                                               f"{refs['threshold']},{rng('C')},{refs['buffer']})", NUM,
         "First-order: next departure only"),
        ("Share of propagated delay avoided", "=IF(B6=0,0,B7/B6)", PCT, ""),
        ("Airline cost avoided ($)", f"=B7*{refs['gate']}", USD, "Avoided minutes are gate waiting time"),
        ("Passenger time saved ($)", f"=B7*{refs['pax']}", USD, ""),
        ("Cost of the extra ground time ($)", f"=B5*{refs['buffer']}*{refs['ground']}", USD,
         "Turns x minutes added x cost per ground minute"),
        ("Net benefit to the airline ($)", "=B9-B11", USD, "Airline cost avoided minus buffer cost"),
        ("Net benefit including passengers ($)", "=B9+B10-B11", USD, ""),
        ("Break-even cost per ground minute ($)", f"=IF(B5*{refs['buffer']}=0,0,B9/(B5*{refs['buffer']}))", USD2,
         "Buffer pays for the airline when the true ground-minute cost is below this"),
    ]
    for i, (label, formula, fmt, note) in enumerate(lines, start=5):
        _c(sc, f"A{i}", label)
        _c(sc, f"B{i}", formula, fmt=fmt)
        if fmt in (NUM, USD) and "Share" not in label:
            _c(sc, f"C{i}", f"=B{i}*12/{refs['months']}", fmt=fmt)
        _c(sc, f"D{i}", note)
    sc.conditional_formatting.add("B12:C13", CellIsRule(operator="greaterThan", formula=["0"], fill=GOOD))
    sc.conditional_formatting.add("B12:C13", CellIsRule(operator="lessThan", formula=["0"], fill=BAD))
    g0 = 18
    _c(sc, f"A{g0}", "Net benefit to the airline per year ($) for the chosen carrier: threshold (rows) x minutes added "
                    "(columns)", bold=True)
    _head(sc, g0 + 1, ["Threshold"] + [f"+{x} min" for x in config.BUFFER_MINUTES])
    for i, thr in enumerate(config.TURN_THRESHOLDS, start=g0 + 2):
        _c(sc, f"A{i}", thr, BLUE, "0")
        for j, buf in enumerate(config.BUFFER_MINUTES):
            col = chr(ord("B") + j)
            avoided = f"SUMIFS({rng('G')},{rng('A')},{refs['carrier']},{rng('H')},{refs['window']},{rng('B')},$A{i},{rng('C')},{buf})"
            turns = f"SUMIFS({rng('D')},{rng('A')},{refs['carrier']},{rng('H')},{refs['window']},{rng('B')},$A{i},{rng('C')},{buf})"
            _c(sc, f"{col}{i}", f"=({avoided}*{refs['gate']}-{turns}*{buf}*{refs['ground']})*12/{refs['months']}", fmt=USD)
    gl = g0 + 1 + len(config.TURN_THRESHOLDS)
    sc.conditional_formatting.add(f"B{g0 + 2}:F{gl}", CellIsRule(operator="greaterThan", formula=["0"], fill=GOOD))
    sc.conditional_formatting.add(f"B{g0 + 2}:F{gl}", CellIsRule(operator="lessThan", formula=["0"], fill=BAD))
    _widths(sc, {"A": 44, "B": 18, "C": 18, "D": 60, "E": 16, "F": 16})

    # ------------------------------------------------------------------ Carrier turns
    ct = wb.create_sheet("Carrier turns")
    _c(ct, "A1", "Aircraft turns by carrier (pasted from reports/tables/carrier_turns.csv)", bold=True, size=14)
    _head(ct, 3, ["Carrier", "Linked turns", "Median scheduled turn (min)", "Minimum turn (min)",
                  "Share with slack of 15 min or less", "Share of departures with propagated delay",
                  "Propagated minutes", "Own departure delay minutes", "Propagated share of departure delay"])
    for i, r in enumerate(carrier_turns.itertuples(), start=4):
        vals = [r.carrier, int(r.turns), float(r.median_sched_turn), float(r.min_turn), float(r.share_slack_15_or_less),
                float(r.share_with_propagated), float(r.propagated_minutes), float(r.own_departure_minutes)]
        fmts = [None, NUM, "0", "0", PCT, PCT, NUM, NUM]
        for j, (v, f) in enumerate(zip(vals, fmts)):
            cell = ct.cell(row=i, column=1 + j, value=v)
            cell.font = Font(name=ARIAL, color=BLUE)
            if f:
                cell.number_format = f
        _c(ct, f"I{i}", f"=IF(G{i}+H{i}=0,0,G{i}/(G{i}+H{i}))", fmt=PCT)
    _widths(ct, {"A": 9, **{c: 17 for c in "BCDEFGHI"}})

    config.EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    wb.save(config.EXCEL_PATH)
    results.setdefault("excel_layout", {})["carrier_total_row"] = carrier_total_row
    return str(config.EXCEL_PATH.relative_to(config.ROOT))


def expected_totals(results: dict) -> dict[str, float]:
    """Cell values the recalculated workbook must show with the default inputs."""
    t = results["excel_layout"]["carrier_total_row"]
    sc = {(r["carrier"], r["time_window"], r["threshold"], r["buffer"]): r for r in results["buffer"]["rows"]}
    default = sc[(DEFAULT_CARRIER, DEFAULT_WINDOW, DEFAULT_THRESHOLD, DEFAULT_BUFFER)]
    return {f"Carrier delay cost!F{t}": results["network"]["arr_delay_minutes"],
            f"Carrier delay cost!C{t}": results["network"]["scheduled"],
            "Buffer scenario!B5": default["turns_buffered"], "Buffer scenario!B7": default["minutes_avoided"]}
