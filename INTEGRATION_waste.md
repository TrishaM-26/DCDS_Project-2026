# Waste module – integration guide (for the dashboard teammate)

Everything lives in `modules/waste.py`. `import waste` needs only `from modules import waste`.
A working reference page is in `example_waste_dashboard.py` (call `render_waste_section(donor_id)`).
Donor ids are the MySQL `donors.donor_id` values (1–8). `None` = admin / all donors.

## Two kinds of functions
**Commands** (change data) never raise for user mistakes. They return a dict:
```python
{"ok": True, "id": "...", "qty_kg": 2.0}
{"ok": False, "error": "reason must be one of: Expired, Overproduction, Spoiled, Plate Waste, Unsold."}
```
Show `result["error"]` with `st.error(...)`.

**Queries** (read data) return lists. They raise `ValueError` for programmer errors (bad arguments) and
`waste.WasteDBError` when MongoDB cannot be reached – catch the latter and show `str(exc)`.

## Function list
| Function | Returns |
|---|---|
| `log_waste(donor_id, category_id, item, quantity, unit, reason, notes=None, storage_condition=None, recorded_at=None)` | command dict |
| `update_waste_log(log_id, fields, donor_id=None)` | command dict (pass `donor_id` so a donor can only edit own logs) |
| `delete_waste_log(log_id, donor_id=None)` | command dict (same ownership rule) |
| `get_waste_logs(donor_id=None, reason=None, category_id=None, since=None, until=None, limit=50)` | list of log dicts (`id` is a string) |
| `waste_by_reason(donor_id=None, since=None, until=None)` | `[{'reason':'Expired','total_kg':805.8,'logs':86}, ...]` |
| `waste_by_category(...)` | `[{'category':'Rice & Grains (Cooked)','total_kg':549.6,'logs':28}, ...]` |
| `waste_by_month(...)` | `[{'month':'2026-06','total_kg':650.65,'logs':51}, ...]` oldest first |
| `waste_totals_by_donor(since=None, until=None)` | `[{'donor_id':5,'total_kg':593.65,'logs':60}, ...]` (old name `waste_by_donor_id` still works) |
| `high_waste_donors(threshold_kg=None, since=None, until=None)` | same shape, only donors at/above threshold (default `waste.HIGH_WASTE_KG` = 400) |
| `waste_logs_to_csv_text(logs)` | CSV string (for `st.download_button`) |
| `export_waste_csv(path=None, donor_id=None)` | command dict with file path |

Constants for dropdowns: `waste.CATEGORIES` (id→name), `waste.ALLOWED_REASONS`, `waste.KG_PER_UNIT`
(keys = units), `waste.STORAGE_CONDITIONS`, `waste.VALID_DONOR_IDS`.

## Dates
`since` / `until` are `datetime` objects. `st.date_input` returns a `date`, so convert:
```python
from datetime import datetime, time
since = datetime.combine(start_date, time.min)
until = datetime.combine(end_date, time.max)
```
Seed data is fixed Jun–Sep 2026, so a "last 30 days" filter will be empty – use explicit dates in the demo.

## Joining with MySQL (donations vs waste)
```python
import pandas as pd
waste_df = pd.DataFrame(waste.waste_totals_by_donor())          # donor_id, total_kg, logs
donation_df = pd.read_sql("SELECT donor_id, SUM(quantity) AS donated FROM donations GROUP BY donor_id", conn)  # adjust to real table/columns
merged = donation_df.merge(waste_df, on="donor_id", how="outer").fillna(0)
```

## Donor vs admin
Logged-in donor: pass their `donor_id` to every query and to update/delete. Admin: pass `None`.

## Notes
* Tests: `python -m pytest -v` (uses separate `waste_logs_test` collection, never the real data).
* Avoid `use_container_width` (deprecated in recent Streamlit); the example uses neither it nor `width="stretch"`.
