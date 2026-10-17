"""
Tests for modules/waste.py

Run from the project root with the virtual environment active:

    python -m pytest -v

The tests use a SEPARATE collection (waste_logs_test), so they never touch your
real waste_logs data.  The collection is emptied before and after every test.

Optional: set WASTE_TEST_MOCK=1 to run against an in-memory fake MongoDB
(needs `python -m pip install mongomock`) when you have no internet.
"""
import csv
import math
import os
from datetime import datetime, timedelta, timezone

import pytest
from pymongo.errors import OperationFailure, ServerSelectionTimeoutError

from modules import waste

USE_MOCK = os.getenv("WASTE_TEST_MOCK") == "1"


def _without_round(node):
    """Replace {"$round": [expr, n]} by expr.

    The in-memory fake MongoDB does not implement $round (a real server does),
    so in mock mode the rounding step is skipped.  Every total used in these
    tests is exactly representable, so the assertions are unaffected.
    """
    if isinstance(node, dict):
        if set(node) == {"$round"}:
            return _without_round(node["$round"][0])
        return {key: _without_round(value) for key, value in node.items()}
    if isinstance(node, list):
        return [_without_round(value) for value in node]
    return node


class _MockCollection:
    def __init__(self, inner):
        self._inner = inner

    def aggregate(self, pipeline, *args, **kwargs):
        return self._inner.aggregate(_without_round(pipeline), *args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._inner, name)


@pytest.fixture
def col(monkeypatch):
    """An empty test collection, cleaned up afterwards."""
    if USE_MOCK:
        import mongomock
        store = mongomock.MongoClient()["test_db"]
        monkeypatch.setattr(waste, "get_collection",
                            lambda name: _MockCollection(store[name]))
    monkeypatch.setattr(waste, "COLLECTION_NAME", "waste_logs_test")
    collection = waste._collection()
    collection.delete_many({})
    yield collection
    collection.delete_many({})


def _dt(year, month, day):
    return datetime(year, month, day, 12, 0, 0)


@pytest.fixture
def known(col):
    """Six logs with hand-calculated totals (59.5 kg in total)."""
    def doc(donor, cat, reason, kg, when):
        return {"donor_id": donor, "category_id": cat, "category": waste.CATEGORIES[cat],
                "item": "x", "quantity": kg, "unit": "kg", "qty_kg": kg,
                "reason": reason, "recorded_at": when}
    col.insert_many([
        doc(1, 1, "Overproduction", 10.0, _dt(2026, 6, 10)),
        doc(1, 2, "Unsold",          5.0, _dt(2026, 6, 20)),
        doc(2, 1, "Overproduction", 20.0, _dt(2026, 7, 5)),
        doc(2, 3, "Expired",         8.0, _dt(2026, 7, 15)),
        doc(3, 3, "Expired",        12.5, _dt(2026, 7, 20)),
        doc(3, 1, "Spoiled",         4.0, _dt(2026, 8, 1)),
    ])
    return col


GOOD = dict(donor_id=3, category_id=1, item="Dal tadka", quantity=20,
            unit="plates", reason="Overproduction")


# ---------------------------------------------------------------- create
def test_t01_valid_log_is_stored_correctly(col):
    result = waste.log_waste(**GOOD, notes="  Event cancelled  ", storage_condition="Hot")
    assert result["ok"] is True
    assert result["qty_kg"] == 8.0                       # 20 plates x 0.4 kg
    stored = col.find_one()
    assert str(stored["_id"]) == result["id"]
    assert stored["category"] == "Cooked Meals"
    assert stored["estimated_cost"] == 1200.0            # 8 kg x Rs 150
    assert isinstance(stored["recorded_at"], datetime)   # a real date, not text
    assert stored["notes"] == "Event cancelled"          # trimmed
    assert stored["storage_condition"] == "Hot"


def test_t01b_optional_fields_are_absent_when_not_given(col):
    waste.log_waste(**GOOD)
    stored = col.find_one()
    assert "notes" not in stored and "storage_condition" not in stored


BAD_INPUTS = [
    ("T02 negative quantity", {"quantity": -5}, "greater than 0"),
    ("T03 zero quantity", {"quantity": 0}, "greater than 0"),
    ("T04 text quantity", {"quantity": "abc"}, "must be a number"),
    ("T05 missing quantity", {"quantity": None}, "must be a number"),
    ("T06 boolean quantity", {"quantity": True}, "must be a number"),
    ("T07 nan quantity", {"quantity": float("nan")}, "must be a number"),
    ("T07b infinite quantity", {"quantity": math.inf}, "must be a number"),
    ("T07c huge quantity", {"quantity": 99999}, "cannot exceed"),
    ("T08 unknown reason", {"reason": "Burnt"}, "reason must be"),
    ("T09 lowercase reason", {"reason": "expired"}, "reason must be"),
    ("T10 unknown unit", {"unit": "litres"}, "unit must be"),
    ("T10b wrong-case unit", {"unit": "Kg"}, "unit must be"),
    ("T11 unknown donor", {"donor_id": 99}, "unknown donor"),
    ("T12 donor as text", {"donor_id": "3"}, "whole number"),
    ("T12b donor as boolean", {"donor_id": True}, "whole number"),
    ("T13 blank item", {"item": "   "}, "item"),
    ("T14 overlong notes", {"notes": "x" * 500}, "notes"),
    ("T15 unknown category", {"category_id": 42}, "category_id"),
    ("T15b unknown storage", {"storage_condition": "Frozen"}, "storage_condition"),
    ("T15c future date", {"recorded_at": datetime.now(timezone.utc) + timedelta(days=1)},
     "future"),
]


@pytest.mark.parametrize("label,change,expected", BAD_INPUTS, ids=[b[0] for b in BAD_INPUTS])
def test_bad_input_is_rejected_without_crashing(col, label, change, expected):
    result = waste.log_waste(**{**GOOD, **change})
    assert result["ok"] is False
    assert expected in result["error"].lower()
    assert col.count_documents({}) == 0                   # nothing was stored


# ---------------------------------------------------------------- read
def test_t16_get_logs_filters_sorts_and_limits(known):
    rows = waste.get_waste_logs(donor_id=2)
    assert [r["qty_kg"] for r in rows] == [8.0, 20.0]            # newest first (15 Jul, 5 Jul)
    assert all(r["donor_id"] == 2 for r in rows)
    assert all(isinstance(r["id"], str) and "_id" not in r for r in rows)
    assert len(waste.get_waste_logs(limit=3)) == 3
    assert len(waste.get_waste_logs(reason="Expired")) == 2
    assert len(waste.get_waste_logs(since=_dt(2026, 7, 1))) == 4


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": "5"}, {"limit": 100000},
                                    {"donor_id": 99}, {"reason": "nope"}, {"since": "2026-07-01"}])
def test_t17_bad_query_arguments_raise_value_error(known, kwargs):
    with pytest.raises(ValueError):
        waste.get_waste_logs(**kwargs)


# ---------------------------------------------------------------- update
def test_t18_update_recomputes_derived_fields(col):
    log_id = waste.log_waste(**GOOD)["id"]
    result = waste.update_waste_log(log_id, {"quantity": 10, "unit": "packets"})
    assert result["ok"] is True
    stored = col.find_one()
    assert stored["qty_kg"] == 2.5                        # 10 packets x 0.25
    assert stored["estimated_cost"] == 375.0              # 2.5 kg x Rs 150
    waste.update_waste_log(log_id, {"category_id": 3})
    stored = col.find_one()
    assert stored["category"] == "Dairy Products" and stored["estimated_cost"] == 300.0


def test_t19_update_can_remove_optional_fields(col):
    log_id = waste.log_waste(**GOOD, notes="hello")["id"]
    assert waste.update_waste_log(log_id, {"notes": None})["ok"] is True
    assert "notes" not in col.find_one()


def test_t20_update_rejects_forbidden_missing_and_invalid(col):
    log_id = waste.log_waste(**GOOD)["id"]
    assert "cannot be edited" in waste.update_waste_log(log_id, {"donor_id": 5})["error"]
    assert "cannot be edited" in waste.update_waste_log(log_id, {"qty_kg": 999})["error"]
    assert waste.update_waste_log(log_id, {"quantity": -1})["ok"] is False
    assert waste.update_waste_log(log_id, {})["ok"] is False
    assert waste.update_waste_log("xyz", {"notes": "a"})["ok"] is False
    assert waste.update_waste_log(None, {"notes": "a"})["ok"] is False
    missing = "0" * 24
    assert waste.update_waste_log(missing, {"notes": "a"})["error"] == "Log not found."


def test_t21_ownership_is_enforced_when_donor_id_is_given(col):
    log_id = waste.log_waste(**GOOD)["id"]                 # belongs to donor 3
    assert waste.update_waste_log(log_id, {"notes": "x"}, donor_id=4)["ok"] is False
    assert waste.delete_waste_log(log_id, donor_id=4)["ok"] is False
    assert col.count_documents({}) == 1
    assert waste.update_waste_log(log_id, {"notes": "x"}, donor_id=3)["ok"] is True
    assert waste.delete_waste_log(log_id, donor_id=3)["ok"] is True


# ---------------------------------------------------------------- delete
def test_t22_delete_then_gone_and_bad_ids(col):
    log_id = waste.log_waste(**GOOD)["id"]
    assert waste.delete_waste_log(log_id)["ok"] is True
    assert col.count_documents({}) == 0
    assert waste.delete_waste_log(log_id)["error"] == "Log not found."   # already deleted
    assert waste.delete_waste_log("xyz")["ok"] is False
    assert waste.delete_waste_log(None)["ok"] is False
    assert waste.delete_waste_log(12345)["ok"] is False


# ---------------------------------------------------------------- aggregations
def test_t23_by_reason_totals(known):
    rows = {r["reason"]: r for r in waste.waste_by_reason()}
    assert rows["Overproduction"]["total_kg"] == 30.0 and rows["Overproduction"]["logs"] == 2
    assert rows["Expired"]["total_kg"] == 20.5 and rows["Unsold"]["total_kg"] == 5.0
    assert sum(r["logs"] for r in rows.values()) == 6
    assert "_id" not in waste.waste_by_reason()[0]                    # _id hidden
    assert waste.waste_by_reason()[0]["reason"] == "Overproduction"   # biggest first


def test_t24_by_category_and_donor_totals(known):
    cats = {r["category"]: r["total_kg"] for r in waste.waste_by_category()}
    assert cats == {"Cooked Meals": 34.0, "Dairy Products": 20.5, "Bakery Items": 5.0}
    donors = {r["donor_id"]: r["total_kg"] for r in waste.waste_totals_by_donor()}
    assert donors == {1: 15.0, 2: 28.0, 3: 16.5}
    assert waste.waste_by_donor_id is waste.waste_totals_by_donor     # old name still works


def test_t25_by_month_is_oldest_first(known):
    rows = waste.waste_by_month()
    assert [r["month"] for r in rows] == ["2026-06", "2026-07", "2026-08"]
    assert [r["total_kg"] for r in rows] == [15.0, 40.5, 4.0]


def test_t26_donor_and_date_filters_narrow_results(known):
    only_donor_2 = waste.waste_by_reason(donor_id=2)
    assert {r["reason"]: r["total_kg"] for r in only_donor_2} == {"Overproduction": 20.0,
                                                                  "Expired": 8.0}
    july_on = waste.waste_by_reason(since=_dt(2026, 7, 1))
    assert sum(r["logs"] for r in july_on) == 4
    window = waste.waste_by_month(since=_dt(2026, 7, 1), until=_dt(2026, 7, 31))
    assert [r["month"] for r in window] == ["2026-07"]


def test_t27_donor_without_logs_gives_empty_list_and_empty_db_too(known, col):
    assert waste.waste_by_reason(donor_id=8) == []
    col.delete_many({})
    assert waste.waste_by_month() == []
    assert waste.high_waste_donors(0) == []


def test_t28_high_waste_alert_thresholds(known):
    flagged = waste.high_waste_donors(20)
    assert [(r["donor_id"], r["total_kg"]) for r in flagged] == [(2, 28.0)]
    assert [r["donor_id"] for r in waste.high_waste_donors(16.5)] == [2, 3]   # inclusive
    assert len(waste.high_waste_donors(0)) == 3
    assert waste.high_waste_donors(1000) == []
    assert [r["donor_id"] for r in waste.high_waste_donors(
        10, since=_dt(2026, 7, 1))] == [2, 3]       # donor 1 only has June logs
    for bad in (-1, "50", True, math.nan):
        with pytest.raises(ValueError):
            waste.high_waste_donors(bad)


# ---------------------------------------------------------------- CSV
def test_t29_csv_export_content_and_row_count(known, tmp_path):
    target = tmp_path / "out" / "logs.csv"
    result = waste.export_waste_csv(str(target))
    assert result == {"ok": True, "path": str(target), "rows": 6}
    with open(target, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert list(rows[0]) == waste.CSV_COLUMNS
    assert rows[0]["recorded_at"] == "2026-08-01 12:00"              # newest first, readable
    only = waste.export_waste_csv(str(tmp_path / "d1.csv"), donor_id=1)
    assert only["rows"] == 2


def test_t30_csv_export_problems_return_messages(known, tmp_path):
    assert waste.export_waste_csv(str(tmp_path / "x.csv"), donor_id=99)["ok"] is False
    # a path inside a *file* cannot be created -> friendly error, no crash
    blocker = tmp_path / "blocker"
    blocker.write_text("a file, not a folder")
    result = waste.export_waste_csv(str(blocker / "x.csv"))
    assert result["ok"] is False and "Could not write" in result["error"]
    assert waste.waste_logs_to_csv_text([]).splitlines() == [",".join(waste.CSV_COLUMNS)]


# ---------------------------------------------------------------- database failure
class _BrokenCollection:
    """Behaves like a collection whose calls all raise the given error."""
    def __init__(self, error):
        self._error = error

    def __getattr__(self, name):
        def fail(*args, **kwargs):
            raise self._error
        return fail


def test_t31_database_outage_gives_friendly_errors(monkeypatch):
    broken = _BrokenCollection(ServerSelectionTimeoutError("simulated outage"))
    monkeypatch.setattr(waste, "_collection", lambda: broken)
    assert waste.log_waste(**GOOD) == {"ok": False, "error": waste.DB_UNAVAILABLE}
    assert waste.update_waste_log("0" * 24, {"notes": "a"})["error"] == waste.DB_UNAVAILABLE
    assert waste.delete_waste_log("0" * 24)["error"] == waste.DB_UNAVAILABLE
    assert waste.export_waste_csv("unused.csv")["error"] == waste.DB_UNAVAILABLE
    for query in (waste.get_waste_logs, waste.waste_by_reason, waste.waste_by_month,
                  waste.high_waste_donors, waste.setup_indexes):
        with pytest.raises(waste.WasteDBError) as caught:
            query()
        assert str(caught.value) == waste.DB_UNAVAILABLE


def test_t31b_rejected_request_is_not_reported_as_an_outage(monkeypatch):
    """A server that answers 'no' (e.g. bad pipeline, bad login) is not 'unreachable'."""
    broken = _BrokenCollection(OperationFailure("simulated rejection"))
    monkeypatch.setattr(waste, "_collection", lambda: broken)
    assert waste.log_waste(**GOOD)["error"] == waste.DB_FAILED
    with pytest.raises(waste.WasteDBError) as caught:
        waste.waste_by_reason()
    assert str(caught.value) == waste.DB_FAILED
    assert isinstance(caught.value.__cause__, OperationFailure)    # original error kept


def test_t32_setup_indexes_is_repeatable(col):
    first = waste.setup_indexes()
    second = waste.setup_indexes()
    assert first == second and len(first) == 2
