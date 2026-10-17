"""
Waste monitoring module (MongoDB)
=================================

Everything the rest of the project needs from the ``waste_logs`` collection
lives in this one file.  Other modules (for example the dashboard) only call
the public functions listed below and never touch the database directly.

Public functions
----------------
Commands (return a dict: {"ok": True, ...} or {"ok": False, "error": "..."}):
    log_waste(...)            create one waste log (validated)
    update_waste_log(...)     change allowed fields of one log
    delete_waste_log(...)     delete one log
    export_waste_csv(...)     write logs to a CSV file

Queries (return a list of dicts):
    get_waste_logs(...)       filtered, newest first
    waste_by_reason(...)      total kg and number of logs per reason
    waste_by_category(...)    ... per food category
    waste_by_month(...)       ... per month ("YYYY-MM"), oldest first
    waste_totals_by_donor(...)... per donor
    high_waste_donors(...)    donors whose total reaches a threshold (the alert)

Error design
------------
* A *user mistake* (negative quantity, unknown reason, bad id ...) never raises
  from a command; it returns {"ok": False, "error": "<plain message>"}.
* Queries raise ``ValueError`` for bad arguments and ``WasteDBError`` when the
  database cannot be reached, so the caller can show a friendly message.
* No SQL/NoSQL strings are built from user text; filters are built from
  validated values only.

Why a separate module and not code inside the UI?  Keeping the data logic here
means it can be tested without a browser and reused by any front end.
"""
import csv
import io
import math
import os
from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import ConnectionFailure, PyMongoError

from db.mongo_conn import get_collection

try:  # the threshold may be overridden in config.py (HIGH_WASTE_KG = ...)
    import config
except ImportError:  # keeps this module importable on its own
    config = None


# --------------------------------------------------------------------------
# Settings and reference data (single place to change them)
# --------------------------------------------------------------------------
COLLECTION_NAME = "waste_logs"          # tests point this at a test collection

ALLOWED_REASONS = ["Expired", "Overproduction", "Spoiled", "Plate Waste", "Unsold"]
KG_PER_UNIT = {"kg": 1.0, "plates": 0.4, "packets": 0.25}   # mirrors MySQL unit_conversions
STORAGE_CONDITIONS = ["Hot", "Cold", "Ambient"]

# category_id -> name (mirrors MySQL food_categories; confirm the ids match)
CATEGORIES = {
    1: "Cooked Meals",
    2: "Bakery Items",
    3: "Dairy Products",
    4: "Fruits & Vegetables",
    5: "Packaged Food",
    6: "Beverages",
    7: "Rice & Grains (Cooked)",
    8: "Sweets & Desserts",
}
COST_PER_KG = {1: 150, 2: 200, 3: 120, 4: 40, 5: 180, 6: 80, 7: 70, 8: 300}  # Rs per kg estimate

VALID_DONOR_IDS = range(1, 9)           # donors 1-8 in the MySQL seed data
MAX_QUANTITY = 5000
MAX_ITEM_LENGTH = 80
MAX_NOTES_LENGTH = 200
MAX_LIMIT = 1000

# Total kg at which a donor is flagged by the high-waste alert.  With the seed
# data, donors 5 (about 594 kg) and 3 (about 506 kg) are far above the rest (the
# third highest is about 360 kg), so 400 flags exactly those two.  Override it by
# adding  HIGH_WASTE_KG = <number>  to config.py.
HIGH_WASTE_KG = getattr(config, "HIGH_WASTE_KG", 400)

EDITABLE_FIELDS = ("item", "quantity", "unit", "reason", "category_id",
                   "storage_condition", "notes")

CSV_COLUMNS = ["id", "donor_id", "category_id", "category", "item", "quantity",
               "unit", "qty_kg", "reason", "recorded_at", "estimated_cost",
               "storage_condition", "notes"]

DB_UNAVAILABLE = "Could not reach the waste database. Check your connection and try again."
DB_FAILED = "The waste database could not complete the request."


class WasteError(Exception):
    """Base class for errors raised by this module."""


class WasteDBError(WasteError):
    """The database could not be reached or the operation failed."""


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def _collection():
    return get_collection(COLLECTION_NAME)


def _fail(message):
    return {"ok": False, "error": message}


def _db_message(exc):
    """Honest message for a PyMongo error: unreachable server vs. failed request.

    Connection problems (server down, no internet, IP not allowed in Atlas)
    raise ConnectionFailure or a subclass.  Anything else (a rejected command,
    a bad login) means the server answered but refused.
    """
    return DB_UNAVAILABLE if isinstance(exc, ConnectionFailure) else DB_FAILED


def _utc_now():
    return datetime.now(timezone.utc)


def _as_utc(value):
    """Treat naive datetimes as UTC (that is how PyMongo stores them)."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_whole_number(value):
    # bool is a subclass of int in Python, so True would otherwise pass
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isfinite(value))


def _to_kg(quantity, unit):
    return round(quantity * KG_PER_UNIT[unit], 2)


def _to_object_id(log_id):
    """Return an ObjectId, or None if the text is not a valid id.

    ObjectId(None) silently creates a brand-new id, so non-text is rejected
    explicitly instead of being passed through.
    """
    if isinstance(log_id, ObjectId):
        return log_id
    if not isinstance(log_id, str) or not ObjectId.is_valid(log_id):
        return None
    return ObjectId(log_id)


def _id_filter(oid, donor_id):
    """Filter for one log; adds the donor when ownership must be enforced."""
    flt = {"_id": oid}
    if donor_id is not None:
        flt["donor_id"] = donor_id
    return flt


# --------------------------------------------------------------------------
# Validation: each _check_* returns an error message, or None when fine
# --------------------------------------------------------------------------
def _check_donor_id(value):
    if not _is_whole_number(value):
        return "donor_id must be a whole number."
    if value not in VALID_DONOR_IDS:
        return f"Unknown donor_id {value}."
    return None


def _check_category_id(value):
    if not _is_whole_number(value) or value not in CATEGORIES:
        return "category_id must be one of: " + ", ".join(
            f"{k} ({v})" for k, v in CATEGORIES.items()) + "."
    return None


def _check_item(value):
    if not isinstance(value, str) or not value.strip():
        return "item must be non-empty text."
    if len(value.strip()) > MAX_ITEM_LENGTH:
        return f"item must be at most {MAX_ITEM_LENGTH} characters."
    return None


def _check_quantity(value):
    if not _is_number(value):
        return "quantity must be a number."
    if value <= 0:
        return "quantity must be greater than 0."
    if value > MAX_QUANTITY:
        return f"quantity cannot exceed {MAX_QUANTITY}."
    return None


def _check_unit(value):
    if not isinstance(value, str) or value not in KG_PER_UNIT:
        return "unit must be one of: " + ", ".join(KG_PER_UNIT) + "."
    return None


def _check_reason(value):
    if not isinstance(value, str) or value not in ALLOWED_REASONS:
        return "reason must be one of: " + ", ".join(ALLOWED_REASONS) + "."
    return None


def _check_storage(value):
    if value is None:
        return None
    if not isinstance(value, str) or value not in STORAGE_CONDITIONS:
        return "storage_condition must be one of: " + ", ".join(STORAGE_CONDITIONS) + "."
    return None


def _check_notes(value):
    if value is None:
        return None
    if not isinstance(value, str):
        return "notes must be text."
    if len(value.strip()) > MAX_NOTES_LENGTH:
        return f"notes must be at most {MAX_NOTES_LENGTH} characters."
    return None


def _check_recorded_at(value):
    if value is None:
        return None
    if not isinstance(value, datetime):
        return "recorded_at must be a date and time."
    if _as_utc(value) > _utc_now():
        return "recorded_at cannot be in the future."
    return None


def _first_error(pairs):
    """Run (check, value) pairs in order and return the first error found."""
    for check, value in pairs:
        error = check(value)
        if error:
            return error
    return None


_UPDATE_CHECKS = {
    "item": _check_item,
    "quantity": _check_quantity,
    "unit": _check_unit,
    "reason": _check_reason,
    "category_id": _check_category_id,
    "storage_condition": _check_storage,
    "notes": _check_notes,
}


# --------------------------------------------------------------------------
# Commands: create, update, delete
# --------------------------------------------------------------------------
def log_waste(donor_id, category_id, item, quantity, unit, reason,
              notes=None, storage_condition=None, recorded_at=None):
    """Validate and store one waste log.

    Returns {"ok": True, "id": "<log id>", "qty_kg": <float>} on success or
    {"ok": False, "error": "<message>"} on any problem.  qty_kg (the quantity
    converted to kilograms) is stored so every report can simply sum it.
    """
    error = _first_error([
        (_check_donor_id, donor_id),
        (_check_category_id, category_id),
        (_check_item, item),
        (_check_quantity, quantity),
        (_check_unit, unit),
        (_check_reason, reason),
        (_check_storage, storage_condition),
        (_check_notes, notes),
        (_check_recorded_at, recorded_at),
    ])
    if error:
        return _fail(error)

    qty_kg = _to_kg(quantity, unit)
    doc = {
        "donor_id": donor_id,
        "category_id": category_id,
        "category": CATEGORIES[category_id],
        "item": item.strip(),
        "quantity": quantity,
        "unit": unit,
        "qty_kg": qty_kg,
        "reason": reason,
        "recorded_at": recorded_at if recorded_at is not None else _utc_now(),
        "estimated_cost": round(qty_kg * COST_PER_KG[category_id], 2),
    }
    # Optional fields are only stored when given (flexible schema).
    if isinstance(notes, str) and notes.strip():
        doc["notes"] = notes.strip()
    if storage_condition:
        doc["storage_condition"] = storage_condition

    try:
        result = _collection().insert_one(doc)
    except PyMongoError as exc:
        return _fail(_db_message(exc))
    return {"ok": True, "id": str(result.inserted_id), "qty_kg": qty_kg}


def update_waste_log(log_id, fields, donor_id=None):
    """Change some fields of one log.

    ``fields`` may only contain: item, quantity, unit, reason, category_id,
    storage_condition, notes.  qty_kg, category name and estimated cost are
    derived values, so they are recomputed whenever quantity, unit or category
    change.  Passing None (or empty text) for notes/storage_condition removes
    the field.  If ``donor_id`` is given, only that donor's own log can be
    changed (use it for the donor role; leave it None for an admin).
    """
    if not isinstance(fields, dict) or not fields:
        return _fail("No changes were given.")
    unknown = sorted(str(k) for k in fields if k not in EDITABLE_FIELDS)
    if unknown:
        return _fail("These fields cannot be edited: " + ", ".join(unknown) + ".")
    oid = _to_object_id(log_id)
    if oid is None:
        return _fail("That is not a valid log id.")
    if donor_id is not None:
        error = _check_donor_id(donor_id)
        if error:
            return _fail(error)
    error = _first_error([(_UPDATE_CHECKS[name], value) for name, value in fields.items()])
    if error:
        return _fail(error)

    try:
        collection = _collection()
        flt = _id_filter(oid, donor_id)
        current = collection.find_one(flt)
        if current is None:
            return _fail("Log not found.")

        sets, unsets = {}, {}
        for name, value in fields.items():
            if name in ("notes", "storage_condition"):
                if value is None or (isinstance(value, str) and not value.strip()):
                    unsets[name] = ""
                else:
                    sets[name] = value.strip() if name == "notes" else value
            elif name == "item":
                sets[name] = value.strip()
            else:
                sets[name] = value

        if {"quantity", "unit", "category_id"} & set(sets):
            quantity = sets.get("quantity", current.get("quantity"))
            unit = sets.get("unit", current.get("unit"))
            category_id = sets.get("category_id", current.get("category_id"))
            if (not _is_number(quantity) or unit not in KG_PER_UNIT
                    or category_id not in CATEGORIES):
                return _fail("The stored log is incomplete and cannot be recalculated.")
            qty_kg = _to_kg(quantity, unit)
            sets["qty_kg"] = qty_kg
            sets["estimated_cost"] = round(qty_kg * COST_PER_KG[category_id], 2)
            sets["category"] = CATEGORIES[category_id]

        operation = {}
        if sets:
            operation["$set"] = sets
        if unsets:
            operation["$unset"] = unsets
        collection.update_one(flt, operation)
    except PyMongoError as exc:
        return _fail(_db_message(exc))
    return {"ok": True, "id": str(oid), "updated": sorted(fields)}


def delete_waste_log(log_id, donor_id=None):
    """Delete exactly one log by id (never "delete many").

    If ``donor_id`` is given, only that donor's own log can be deleted.
    """
    oid = _to_object_id(log_id)
    if oid is None:
        return _fail("That is not a valid log id.")
    if donor_id is not None:
        error = _check_donor_id(donor_id)
        if error:
            return _fail(error)
    try:
        result = _collection().delete_one(_id_filter(oid, donor_id))
    except PyMongoError as exc:
        return _fail(_db_message(exc))
    if result.deleted_count == 0:
        return _fail("Log not found.")
    return {"ok": True, "id": str(oid)}


# --------------------------------------------------------------------------
# Queries
# --------------------------------------------------------------------------
def _require_valid(error):
    if error:
        raise ValueError(error)


def _check_date_arg(value, name):
    if value is not None and not isinstance(value, datetime):
        raise ValueError(f"{name} must be a datetime.")


def _build_filter(donor_id=None, reason=None, category_id=None, since=None, until=None):
    """Build a MongoDB filter from validated arguments (raises ValueError)."""
    flt = {}
    if donor_id is not None:
        _require_valid(_check_donor_id(donor_id))
        flt["donor_id"] = donor_id
    if reason is not None:
        _require_valid(_check_reason(reason))
        flt["reason"] = reason
    if category_id is not None:
        _require_valid(_check_category_id(category_id))
        flt["category_id"] = category_id
    _check_date_arg(since, "since")
    _check_date_arg(until, "until")
    if since is not None or until is not None:
        window = {}
        if since is not None:
            window["$gte"] = since
        if until is not None:
            window["$lte"] = until
        flt["recorded_at"] = window
    return flt


def _find_logs(flt, limit):
    try:
        cursor = _collection().find(flt).sort("recorded_at", -1)
        if limit is not None:
            cursor = cursor.limit(limit)
        rows = list(cursor)
    except PyMongoError as exc:
        raise WasteDBError(_db_message(exc)) from exc
    for row in rows:                       # ObjectId is not display/JSON friendly
        row["id"] = str(row.pop("_id"))
    return rows


def get_waste_logs(donor_id=None, reason=None, category_id=None,
                   since=None, until=None, limit=50):
    """Return logs (newest first) as a list of dicts, each with a text "id"."""
    if limit is not None and (not _is_whole_number(limit) or not 1 <= limit <= MAX_LIMIT):
        raise ValueError(f"limit must be a whole number from 1 to {MAX_LIMIT}.")
    flt = _build_filter(donor_id, reason, category_id, since, until)
    return _find_logs(flt, limit)


def _run(pipeline, donor_id=None, since=None, until=None):
    """Run an aggregation pipeline, optionally narrowed by donor / date range.

    The $match goes FIRST: $group collapses many logs into a few rows, after
    which donor_id and recorded_at no longer exist to filter on, and filtering
    early also means fewer documents flow through the later stages.
    """
    flt = _build_filter(donor_id=donor_id, since=since, until=until)
    if flt:
        pipeline.insert(0, {"$match": flt})
    try:
        return list(_collection().aggregate(pipeline))
    except PyMongoError as exc:
        raise WasteDBError(_db_message(exc)) from exc


def waste_by_reason(donor_id=None, since=None, until=None):
    """[{"reason", "total_kg", "logs"}, ...] biggest total first."""
    pipeline = [
        {"$group": {"_id": "$reason",
                    "total_kg": {"$sum": "$qty_kg"},
                    "logs": {"$sum": 1}}},
        {"$sort": {"total_kg": -1}},
        {"$project": {"_id": 0, "reason": "$_id",
                      "total_kg": {"$round": ["$total_kg", 2]}, "logs": 1}},
    ]
    return _run(pipeline, donor_id, since, until)


def waste_by_category(donor_id=None, since=None, until=None):
    """[{"category", "total_kg", "logs"}, ...] biggest total first."""
    pipeline = [
        {"$group": {"_id": "$category",
                    "total_kg": {"$sum": "$qty_kg"},
                    "logs": {"$sum": 1}}},
        {"$sort": {"total_kg": -1}},
        {"$project": {"_id": 0, "category": "$_id",
                      "total_kg": {"$round": ["$total_kg", 2]}, "logs": 1}},
    ]
    return _run(pipeline, donor_id, since, until)


def waste_by_month(donor_id=None, since=None, until=None):
    """[{"month": "YYYY-MM", "total_kg", "logs"}, ...] oldest month first.

    Oldest-first because this is a trend: charts plot rows in the order given.
    """
    pipeline = [
        {"$group": {"_id": {"$dateToString": {"format": "%Y-%m", "date": "$recorded_at"}},
                    "total_kg": {"$sum": "$qty_kg"},
                    "logs": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"_id": 0, "month": "$_id",
                      "total_kg": {"$round": ["$total_kg", 2]}, "logs": 1}},
    ]
    return _run(pipeline, donor_id, since, until)


def waste_totals_by_donor(donor_id=None, since=None, until=None):
    """[{"donor_id", "total_kg", "logs"}, ...] biggest total first."""
    pipeline = [
        {"$group": {"_id": "$donor_id",
                    "total_kg": {"$sum": "$qty_kg"},
                    "logs": {"$sum": 1}}},
        {"$sort": {"total_kg": -1}},
        {"$project": {"_id": 0, "donor_id": "$_id",
                      "total_kg": {"$round": ["$total_kg", 2]}, "logs": 1}},
    ]
    return _run(pipeline, donor_id, since, until)


waste_by_donor_id = waste_totals_by_donor      # old name kept so nothing breaks


def high_waste_donors(threshold_kg=None, since=None, until=None):
    """Donors whose total waste is at least ``threshold_kg`` (the alert).

    Uses the same per-donor grouping, then a $match AFTER the $group (the
    MongoDB equivalent of SQL's HAVING).  An empty list means nobody crossed
    the threshold.  Pass ``since`` to limit the alert to a period.
    """
    if threshold_kg is None:
        threshold_kg = HIGH_WASTE_KG
    if not _is_number(threshold_kg) or threshold_kg < 0:
        raise ValueError("threshold_kg must be a number that is 0 or more.")
    pipeline = [
        {"$group": {"_id": "$donor_id",
                    "total_kg": {"$sum": "$qty_kg"},
                    "logs": {"$sum": 1}}},
        {"$match": {"total_kg": {"$gte": threshold_kg}}},
        {"$sort": {"total_kg": -1}},
        {"$project": {"_id": 0, "donor_id": "$_id",
                      "total_kg": {"$round": ["$total_kg", 2]}, "logs": 1}},
    ]
    return _run(pipeline, since=since, until=until)


# --------------------------------------------------------------------------
# CSV export (file handling)
# --------------------------------------------------------------------------
def waste_logs_to_csv_text(logs):
    """Turn a list of log dicts into CSV text (also usable for a download button)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CSV_COLUMNS,
                            restval="", extrasaction="ignore")
    writer.writeheader()
    for log in logs:
        row = dict(log)
        if isinstance(row.get("recorded_at"), datetime):
            row["recorded_at"] = row["recorded_at"].strftime("%Y-%m-%d %H:%M")
        writer.writerow(row)
    return buffer.getvalue()


def export_waste_csv(path=None, donor_id=None):
    """Write logs (all, or one donor's) to a CSV file.

    Default path: exports/waste_logs_<timestamp>.csv.  Returns
    {"ok": True, "path": ..., "rows": n} or {"ok": False, "error": ...}.
    """
    try:
        flt = _build_filter(donor_id=donor_id)
        rows = _find_logs(flt, limit=None)
    except ValueError as exc:
        return _fail(str(exc))
    except WasteDBError as exc:
        return _fail(str(exc))

    if path is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("exports", f"waste_logs_{stamp}.csv")
    try:
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        # utf-8-sig so Excel shows every character correctly
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            handle.write(waste_logs_to_csv_text(rows))
    except PermissionError:
        return _fail(f"Could not write {path}. If the file is open in Excel, close it and try again.")
    except OSError as exc:
        return _fail(f"Could not write {path}: {exc.strerror or exc}.")
    return {"ok": True, "path": path, "rows": len(rows)}


# --------------------------------------------------------------------------
# One-time setup
# --------------------------------------------------------------------------
def setup_indexes():
    """Create indexes that speed up the common filters.  Safe to run repeatedly."""
    try:
        collection = _collection()
        return [collection.create_index("donor_id"),
                collection.create_index([("recorded_at", -1)])]
    except PyMongoError as exc:
        raise WasteDBError(_db_message(exc)) from exc
