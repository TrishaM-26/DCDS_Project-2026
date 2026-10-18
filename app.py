"""
app.py - Streamlit front end for the Food Donation & Waste Monitor.

Data sources
    MySQL   (db/mysql_conn.py)  structured records: donors, surplus, donations
    MongoDB (modules/waste.py)  flexible waste logs and aggregation pipelines

Access
    User           read-only: can view every chart and table, cannot change data
    Administrator  password protected (ADMIN_PASSWORD in .env): can add, edit, delete

Run with:  streamlit run app.py
"""
import hmac
import os
import time as clock
from datetime import date, datetime, time
from decimal import Decimal

import pandas as pd
import streamlit as st

import config  # noqa: F401  (importing it loads the .env file)
from db.mysql_conn import run_query
from modules import waste

# ---------------------------------------------------------------- palette
BLUSH = "#f9edf0"
CHAMPAGNE = "#e6c8b7"
COGNAC = "#c3955b"
AMBER = "#ba6a36"
EMERALD = "#1c3934"
ESPRESSO = "#261311"

PAGE_BG = "#1d1311"        # deepened espresso, not pure black (less glare)
TEXT = "#e8d9d0"           # muted champagne-blush instead of pure white
SAGE = "#5f9a88"           # lightened emerald so "good" bars stay visible

GOOD = SAGE        # donated / healthy series
BAD = AMBER        # waste series

SF_DATE = "sf.listed_at"     # date column for surplus_food queries
DN_DATE = "dn.created_at"    # date column for donations queries

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
MAX_TRIES = 5                # wrong passwords allowed before a short lock
LOCK_SECONDS = 30

st.set_page_config(page_title="Food Donation & Waste Monitor",
                   layout="wide", initial_sidebar_state="expanded")

# ---------------------------------------------------------------- styling
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=Playfair+Display:wght@500;600&display=swap');

html, body, p, label, li, span, button, input, textarea {{ font-family: 'Inter', sans-serif; }}
h1, h2, h3 {{ font-family: 'Playfair Display', serif !important; color: {CHAMPAGNE}; letter-spacing: -0.01em; }}
h1 {{ font-size: 2.2rem !important; font-weight: 600; }}
h3 {{ font-size: 1.3rem !important; margin-top: 0 !important; }}

#MainMenu, footer {{ visibility: hidden; }}
.stApp {{ background: linear-gradient(160deg, {PAGE_BG} 0%, #241714 100%); color: {TEXT}; }}
.block-container {{ padding-top: 2.2rem; max-width: 1200px; }}
.stApp p, .stApp li, .stApp label, .stApp span {{ color: {TEXT}; }}
[data-testid="stCaptionContainer"] {{ color: rgba(232,217,208,.65) !important; }}

/* sidebar */
section[data-testid="stSidebar"] {{ background: #16221f; border-right: 1px solid rgba(230,200,183,.12); }}
section[data-testid="stSidebar"] h3 {{ font-size: 1.05rem !important; color: {COGNAC} !important; }}

/* tabs */
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 1px solid rgba(230,200,183,.2); }}
.stTabs [data-baseweb="tab"] {{ color: rgba(232,217,208,.75); font-weight: 500; }}
.stTabs [aria-selected="true"] {{ color: {COGNAC}; }}

/* translucent film behind charts, tables and metric cards.
   box-sizing + max-width keep the padded box inside its column (fixes the right-edge overflow). */
div[data-testid="stMetric"],
div[data-testid="stVegaLiteChart"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"] {{
    box-sizing: border-box !important;
    width: 100% !important;
    max-width: 100% !important;
    overflow: hidden;
    background: rgba(230,200,183,.07);
    border: 1px solid rgba(230,200,183,.16);
    border-radius: 12px;
    padding: 12px 14px;
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}}
div[data-testid="stVegaLiteChart"] > div {{ max-width: 100% !important; }}
div[data-testid="stMetric"] {{ border-top: 3px solid {COGNAC}; }}
div[data-testid="stMetricLabel"] p {{
    font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; color: {COGNAC}; }}
div[data-testid="stMetricValue"] {{ color: {BLUSH}; font-family: 'Playfair Display', serif; }}

/* forms and alerts get the same soft film */
div[data-testid="stForm"] {{
    background: rgba(230,200,183,.05); border: 1px solid rgba(230,200,183,.14);
    border-radius: 12px; }}
div[data-testid="stAlert"] {{ background: rgba(230,200,183,.09); border-radius: 10px; }}

/* short purpose text under each chart */
.note {{
    border-left: 3px solid {AMBER}; background: rgba(186,106,54,.13);
    padding: .55rem .9rem; margin: .3rem 0 1.1rem; font-size: .86rem;
    border-radius: 0 8px 8px 0; color: {TEXT}; }}
.src {{ font-size: .7rem; text-transform: uppercase; letter-spacing: .09em; color: {COGNAC}; font-weight: 600; }}

/* buttons */
.stButton button, .stDownloadButton button, div[data-testid="stFormSubmitButton"] button {{
    background: {EMERALD}; color: {BLUSH}; border: 1px solid rgba(230,200,183,.25); border-radius: 8px; }}
.stButton button:hover, .stDownloadButton button:hover,
div[data-testid="stFormSubmitButton"] button:hover {{
    background: {AMBER}; border-color: {AMBER}; color: #ffffff; }}
</style>
""", unsafe_allow_html=True)


def note(text):
    """Short purpose text shown under a chart or table."""
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def section(title, source):
    st.markdown(f'<span class="src">{source}</span>', unsafe_allow_html=True)
    st.subheader(title)


# ---------------------------------------------------------------- access control
st.session_state.setdefault("role", None)        # None | "user" | "admin"
st.session_state.setdefault("failed_logins", 0)
st.session_state.setdefault("locked_until", 0.0)


def password_ok(typed):
    """Constant-time comparison against ADMIN_PASSWORD from .env."""
    if not ADMIN_PASSWORD:
        return False
    return hmac.compare_digest(typed.encode("utf-8"), ADMIN_PASSWORD.encode("utf-8"))


def login_gate():
    """Entry page: choose User or Administrator. Administrator needs the password."""
    st.markdown("<style>section[data-testid='stSidebar']{display:none}</style>",
                unsafe_allow_html=True)
    _, mid, _ = st.columns([1, 1.4, 1])
    with mid:
        st.title("Food Donation & Waste Monitor")
        note("Choose how you want to enter. Users can view every chart and table. "
             "Only administrators can add, edit or delete waste logs.")
        who = st.radio("Continue as", ["User", "Administrator"], horizontal=True)

        if who == "User":
            if st.button("Enter dashboard"):
                st.session_state["role"] = "user"
                st.rerun()
            return

        if not ADMIN_PASSWORD:
            st.error("Administrator login is not set up. Add ADMIN_PASSWORD to your .env file "
                     "and restart the app.")
            return

        remaining = st.session_state["locked_until"] - clock.time()
        if remaining > 0:
            st.error(f"Too many wrong attempts. Try again in {int(remaining) + 1} seconds.")
            return

        with st.form("admin_login"):
            typed = st.text_input("Administrator password", type="password")
            submitted = st.form_submit_button("Log in")
        if submitted:
            if password_ok(typed):
                st.session_state["role"] = "admin"
                st.session_state["failed_logins"] = 0
                st.rerun()
            st.session_state["failed_logins"] += 1
            if st.session_state["failed_logins"] >= MAX_TRIES:
                st.session_state["locked_until"] = clock.time() + LOCK_SECONDS
                st.session_state["failed_logins"] = 0
                st.error(f"Too many wrong attempts. Locked for {LOCK_SECONDS} seconds.")
            else:
                st.error("Incorrect password.")


if st.session_state["role"] is None:
    login_gate()
    st.stop()

is_admin = st.session_state["role"] == "admin"


# ---------------------------------------------------------------- data helpers
@st.cache_data(ttl=30, show_spinner=False)
def _cached_sql(query, params):
    rows = run_query(query, params, fetch=True)
    if rows is None:                       # run_query prints the error and returns None
        raise RuntimeError("MySQL query failed")
    return pd.DataFrame(rows)


def sql_df(query, params=()):
    """Run a SELECT and return a DataFrame; shows an error instead of crashing."""
    try:
        df = _cached_sql(query, tuple(params))
    except Exception:
        st.error("Could not read from MySQL. Check that the server is running and .env is correct.")
        return pd.DataFrame()
    for col in df.columns:                 # MySQL DECIMAL -> float so charts work
        if df[col].map(lambda v: isinstance(v, Decimal)).any():
            df[col] = df[col].astype(float)
    return df


def mongo(fn, *args, **kwargs):
    """Call a waste.py function; show a friendly message if MongoDB fails."""
    try:
        return fn(*args, **kwargs)
    except (waste.WasteDBError, ValueError) as exc:
        st.error(str(exc))
        return []


def first(df, col, default=0):
    return df[col].iloc[0] if not df.empty else default


# ---------------------------------------------------------------- sidebar
donors = sql_df("SELECT donor_id, organization_name FROM donors ORDER BY donor_id")
if donors.empty:
    st.stop()
names = dict(zip(donors["donor_id"], donors["organization_name"]))

st.sidebar.markdown("### Session")
st.sidebar.write(f"Signed in as **{'Administrator' if is_admin else 'User'}**")
if st.sidebar.button("Log out"):
    st.session_state["role"] = None
    st.rerun()

st.sidebar.markdown("### Filters")
if is_admin:
    view = st.sidebar.radio("View as", ["Administrator", "Donor"])
else:
    # Not clickable for users: the whole control is disabled and fixed on "Donor".
    st.sidebar.radio("View as", ["Administrator", "Donor"], index=1,
                     disabled=True, key="view_locked")
    st.sidebar.caption("Administrator view needs a login.")
    view = "Donor"

donor_id = None
if view == "Donor":
    donor_id = st.sidebar.selectbox("Donor account", list(names), format_func=names.get)

period = st.sidebar.date_input("Period", value=(date(2026, 6, 1), date.today()))
since = until = None
if isinstance(period, (tuple, list)) and len(period) == 2:
    since = datetime.combine(period[0], time.min)
    until = datetime.combine(period[1], time.max)
else:
    st.sidebar.caption("Select an end date to apply the period.")

st.sidebar.markdown("### Connections")
st.sidebar.write("MySQL: connected")
try:
    waste.get_waste_logs(limit=1)
    st.sidebar.write("MongoDB: connected")
except Exception:
    st.sidebar.write("MongoDB: unreachable")


# ---------------------------------------------------------------- SQL queries
Q_LISTINGS = "SELECT COUNT(*) AS n FROM surplus_food sf WHERE 1=1 {scope}"

Q_DONATED = """
SELECT COUNT(*) AS donations,
       COALESCE(ROUND(SUM(dn.quantity_donated * uc.kg_per_unit), 1), 0) AS donated_kg
FROM donations dn
JOIN surplus_food sf     ON sf.surplus_id = dn.surplus_id
JOIN unit_conversions uc ON uc.unit = sf.unit
WHERE dn.donation_status = 'Completed' {scope}"""

Q_STATUS = """
SELECT sf.status, COUNT(*) AS listings
FROM surplus_food sf WHERE 1=1 {scope}
GROUP BY sf.status ORDER BY listings DESC"""

Q_CATEGORY = """
SELECT fc.category_name AS category, COUNT(*) AS listings,
       ROUND(SUM(sf.quantity * uc.kg_per_unit), 1) AS total_kg
FROM surplus_food sf
JOIN food_categories fc  ON fc.category_id = sf.category_id
JOIN unit_conversions uc ON uc.unit = sf.unit
WHERE 1=1 {scope}
GROUP BY fc.category_name ORDER BY total_kg DESC"""

Q_PIPELINE = """
SELECT dn.donation_id AS id, d.organization_name AS donor, sf.food_name AS food,
       r.organization_name AS receiver, COALESCE(u.name, 'Unassigned') AS volunteer,
       dn.quantity_donated AS quantity, sf.unit, dn.donation_status AS status,
       cr.condition_on_arrival AS arrival_condition, cr.quantity_rejected AS rejected
FROM donations dn
JOIN surplus_food sf ON sf.surplus_id = dn.surplus_id
JOIN donors d        ON d.donor_id = sf.donor_id
JOIN receivers r     ON r.receiver_id = dn.receiver_id
LEFT JOIN volunteers v          ON v.volunteer_id = dn.volunteer_id
LEFT JOIN users u               ON u.user_id = v.user_id
LEFT JOIN collection_records cr ON cr.donation_id = dn.donation_id
WHERE 1=1 {scope}
ORDER BY dn.donation_id"""

Q_QUALITY = """
SELECT cr.condition_on_arrival AS arrival_condition, COUNT(*) AS deliveries,
       ROUND(SUM(cr.quantity_rejected), 2) AS rejected
FROM collection_records cr
JOIN donations dn    ON dn.donation_id = cr.donation_id
JOIN surplus_food sf ON sf.surplus_id = dn.surplus_id
WHERE 1=1 {scope}
GROUP BY cr.condition_on_arrival"""

Q_LARGE = """
SELECT sf.food_name AS food, d.organization_name AS donor,
       ROUND(sf.quantity * uc.kg_per_unit, 1) AS kg
FROM surplus_food sf
JOIN unit_conversions uc ON uc.unit = sf.unit
JOIN donors d            ON d.donor_id = sf.donor_id
WHERE sf.quantity * uc.kg_per_unit >
      (SELECT AVG(s2.quantity * u2.kg_per_unit)
       FROM surplus_food s2 JOIN unit_conversions u2 ON u2.unit = s2.unit)
{scope}
ORDER BY kg DESC"""

Q_DONATED_BY_DONOR = """
SELECT sf.donor_id, ROUND(SUM(dn.quantity_donated * uc.kg_per_unit), 1) AS donated_kg
FROM donations dn
JOIN surplus_food sf     ON sf.surplus_id = dn.surplus_id
JOIN unit_conversions uc ON uc.unit = sf.unit
WHERE dn.donation_status = 'Completed' {scope}
GROUP BY sf.donor_id"""


def run(query, date_col):
    """Run a SQL query narrowed by the selected donor and the sidebar period.

    date_col is a fixed constant from this file (never user input); the donor id
    and the dates travel as parameters.
    """
    clauses, params = [], []
    if donor_id:
        clauses.append("AND sf.donor_id = %s")
        params.append(donor_id)
    if since:
        clauses.append(f"AND {date_col} BETWEEN %s AND %s")
        params += [since, until]
    return sql_df(query.replace("{scope}", " ".join(clauses)), tuple(params))


# ---------------------------------------------------------------- header
st.title("Food Donation & Waste Monitor")
scope_text = "all donors" if donor_id is None else names[donor_id]
access_text = "full access" if is_admin else "read-only"
st.caption(f"Viewing {scope_text}  |  {access_text}  |  period "
           f"{period[0]:%d %b %Y} to {period[1]:%d %b %Y}"
           if since else f"Viewing {scope_text}  |  {access_text}")

tab_over, tab_don, tab_waste, tab_link, tab_manage, tab_about = st.tabs(
    ["Overview", "Donations", "Waste analytics", "Donated vs wasted",
     "Manage waste logs", "About"])

# ---------------------------------------------------------------- Overview
with tab_over:
    by_reason = mongo(waste.waste_by_reason, donor_id, since, until)
    wasted_kg = sum(r["total_kg"] for r in by_reason)
    donated = run(Q_DONATED, DN_DATE)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Surplus listings", int(first(run(Q_LISTINGS, SF_DATE), "n")))
    c2.metric("Completed donations", int(first(donated, "donations")))
    c3.metric("Food donated (kg)", f"{first(donated, 'donated_kg'):,.1f}")
    c4.metric("Waste logged (kg)", f"{wasted_kg:,.1f}")
    note("Top row combines both databases: the first three figures come from MySQL "
         "(listings and donations), the last from MongoDB (waste logs).")

    left, right = st.columns(2)
    with left:
        section("Surplus listings by status", "MySQL")
        status = run(Q_STATUS, SF_DATE)
        if not status.empty:
            st.bar_chart(status.set_index("status")["listings"], color=GOOD)
        else:
            st.info("No listings for this selection.")
        note("Shows how much listed food was actually collected, and how much "
             "expired or was wasted before anyone claimed it.")
    with right:
        section("Waste by reason (kg)", "MongoDB")
        if by_reason:
            st.bar_chart(pd.DataFrame(by_reason).set_index("reason")["total_kg"], color=BAD)
        else:
            st.info("No waste logged for this selection.")
        note("Points to the biggest cause of waste, so prevention effort can go there first.")

# ---------------------------------------------------------------- Donations
with tab_don:
    section("Donation pipeline", "MySQL | 5-table join")
    pipe = run(Q_PIPELINE, DN_DATE)
    if pipe.empty:
        st.info("No donations for this selection.")
    else:
        picked = st.multiselect("Status", sorted(pipe["status"].unique()),
                                default=sorted(pipe["status"].unique()))
        st.dataframe(pipe[pipe["status"].isin(picked)], hide_index=True)
    note("Follows each donation from donor to receiver, with the volunteer who carried it "
         "and the condition it arrived in. Built with JOINs and LEFT JOINs, so donations "
         "without a volunteer or delivery record still appear.")

    a, b = st.columns(2)
    with a:
        section("Surplus by food category", "MySQL | GROUP BY")
        cat = run(Q_CATEGORY, SF_DATE)
        if not cat.empty:
            st.bar_chart(cat.set_index("category")["total_kg"], color=COGNAC)
        note("Total listed weight per category, with units (plates, packets) converted to kg.")
    with b:
        section("Delivery quality", "MySQL | aggregation")
        quality = run(Q_QUALITY, DN_DATE)
        if not quality.empty:
            st.dataframe(quality, hide_index=True)
        note("How deliveries arrived and how much food receivers had to reject.")

    section("Listings larger than the average", "MySQL | nested query")
    large = run(Q_LARGE, SF_DATE)
    if not large.empty:
        st.dataframe(large, hide_index=True)
    note("Uses a subquery to compare each listing with the average listing size, "
         "highlighting bulk surplus that needs a van or several volunteers.")

# ---------------------------------------------------------------- Waste analytics
with tab_waste:
    a, b = st.columns(2)
    with a:
        section("Waste by food category (kg)", "MongoDB | aggregation pipeline")
        by_cat = mongo(waste.waste_by_category, donor_id, since, until)
        if by_cat:
            st.bar_chart(pd.DataFrame(by_cat).set_index("category")["total_kg"], color=BAD)
        note("Pipeline: $match, $group, $sum, $sort, $project. Shows which food types are lost most.")
    with b:
        section("Monthly trend (kg)", "MongoDB | aggregation pipeline")
        by_month = mongo(waste.waste_by_month, donor_id, since, until)
        if by_month:
            st.line_chart(pd.DataFrame(by_month).set_index("month")["total_kg"], color=BAD)
        note("Grouped by month with $dateToString and sorted oldest first, so the line reads as a trend.")

    if donor_id is None:
        section("Waste per donor (kg)", "MongoDB")
        per_donor = pd.DataFrame(mongo(waste.waste_totals_by_donor, None, since, until))
        if not per_donor.empty:
            per_donor["donor"] = per_donor["donor_id"].map(names)
            st.bar_chart(per_donor.set_index("donor")["total_kg"], color=COGNAC)
        note("Compares donors against each other. Donor names are looked up from MySQL.")

    section("Waste log records", "MongoDB")
    logs = mongo(waste.get_waste_logs, donor_id=donor_id, since=since, until=until, limit=200)
    if logs:
        df = pd.DataFrame(logs)
        cols = ["recorded_at", "donor_id", "category", "item", "quantity", "unit",
                "qty_kg", "reason", "estimated_cost", "storage_condition", "notes"]
        st.dataframe(df[[c for c in cols if c in df]], hide_index=True)
        st.download_button("Download as CSV", waste.waste_logs_to_csv_text(logs),
                           "waste_logs.csv", "text/csv")
    else:
        st.info("No waste logs for this selection.")
    note("Optional fields such as notes and storage condition exist only on some logs, "
         "which is the flexibility a document database provides.")

# ---------------------------------------------------------------- Donated vs wasted
with tab_link:
    section("Donated vs wasted, per donor", "MySQL + MongoDB")

    sql_part = run(Q_DONATED_BY_DONOR, DN_DATE).reindex(columns=["donor_id", "donated_kg"])
    sql_part["donor_id"] = sql_part["donor_id"].astype("int64")
    mongo_part = pd.DataFrame(mongo(waste.waste_totals_by_donor, donor_id, since, until),
                              columns=["donor_id", "total_kg", "logs"])
    mongo_part["donor_id"] = mongo_part["donor_id"].astype("int64")

    merged = donors.merge(sql_part, on="donor_id", how="left") \
                   .merge(mongo_part, on="donor_id", how="left").fillna(0)
    if donor_id:
        merged = merged[merged["donor_id"] == donor_id]
    merged = merged.rename(columns={"organization_name": "Donor", "donated_kg": "Donated (kg)",
                                    "total_kg": "Wasted (kg)", "logs": "Waste logs"})
    total = merged["Donated (kg)"] + merged["Wasted (kg)"]
    merged["Lost share (%)"] = (merged["Wasted (kg)"] / total.where(total > 0) * 100).round(1).fillna(0)

    st.bar_chart(merged.set_index("Donor")[["Donated (kg)", "Wasted (kg)"]], color=[GOOD, BAD])
    st.dataframe(merged.drop(columns="donor_id"), hide_index=True)
    note("Donations come from MySQL and waste logs from MongoDB; the two are joined in Python "
         "on donor_id. A high lost share means a donor wastes far more than it passes on.")

    if donor_id is None:
        section("High-waste alert", "MongoDB | $group + $match")
        limit = st.number_input("Alert threshold (kg)", min_value=0.0,
                                value=float(waste.HIGH_WASTE_KG), step=50.0)
        flagged = mongo(waste.high_waste_donors, limit, since, until)
        if not flagged:
            st.success("No donor has reached the threshold.")
        for row in flagged:
            st.warning(f"{names.get(row['donor_id'], row['donor_id'])}: "
                       f"{row['total_kg']:,.1f} kg across {row['logs']} logs")
        note("Works like SQL HAVING: totals are grouped first, then only donors at or above "
             "the threshold are kept.")

# ---------------------------------------------------------------- Manage waste logs
with tab_manage:
    flash = st.session_state.pop("flash", None)
    if flash:
        (st.success if flash[0] == "ok" else st.error)(flash[1])

    if not is_admin:
        # Users can see the records but have no add, edit or delete controls.
        section("Waste logs (read-only)", "MongoDB")
        st.info("Editing is limited to administrators. Log out and choose Administrator "
                "on the entry page to make changes.")
        view_logs = mongo(waste.get_waste_logs, donor_id=donor_id, limit=50)
        if view_logs:
            vdf = pd.DataFrame(view_logs)
            cols = ["recorded_at", "category", "item", "quantity", "unit", "reason",
                    "qty_kg", "estimated_cost", "storage_condition", "notes"]
            st.dataframe(vdf[[c for c in cols if c in vdf]], hide_index=True)
        else:
            st.info("No waste logs for this selection.")
        note("Read-only view of the 50 most recent logs for the selected donor.")
    else:
        section("Add a waste log", "MongoDB | create")
        with st.form("add_log", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            who = donor_id if donor_id else c1.selectbox("Donor", list(names), format_func=names.get)
            category = c2.selectbox("Category", list(waste.CATEGORIES), format_func=waste.CATEGORIES.get)
            item = c3.text_input("Item", max_chars=waste.MAX_ITEM_LENGTH)
            c4, c5, c6 = st.columns(3)
            qty = c4.number_input("Quantity", min_value=0.1, max_value=float(waste.MAX_QUANTITY),
                                  value=1.0, step=0.5)
            unit = c5.selectbox("Unit", list(waste.KG_PER_UNIT))
            reason = c6.selectbox("Reason", waste.ALLOWED_REASONS)
            c7, c8 = st.columns([1, 2])
            storage = c7.selectbox("Storage (optional)", ["-"] + waste.STORAGE_CONDITIONS)
            notes = c8.text_input("Notes (optional)", max_chars=waste.MAX_NOTES_LENGTH)
            if st.form_submit_button("Save log"):
                res = waste.log_waste(who, category, item, qty, unit, reason, notes=notes or None,
                                      storage_condition=None if storage == "-" else storage)
                st.session_state["flash"] = ("ok", f"Saved ({res['qty_kg']} kg).") if res["ok"] \
                    else ("err", res["error"])
                st.rerun()
        note("Every field is validated before it is stored. Invalid input is rejected "
             "with a clear message and nothing is written.")

        section("Edit or delete a log", "MongoDB | update, delete")
        recent = mongo(waste.get_waste_logs, donor_id=donor_id, limit=25)
        if recent:
            by_id = {r["id"]: r for r in recent}
            pick = st.selectbox("Log", list(by_id), format_func=lambda i:
                                f"{by_id[i]['item']} | {by_id[i]['quantity']} {by_id[i]['unit']} | "
                                f"{by_id[i]['reason']} | {by_id[i]['recorded_at']:%d %b %Y}")
            cur = by_id[pick]
            e1, e2, e3 = st.columns(3)
            new_qty = e1.number_input(
                "Quantity ", min_value=0.1, max_value=float(waste.MAX_QUANTITY),
                value=min(max(float(cur["quantity"]), 0.1), float(waste.MAX_QUANTITY)),
                step=0.5, key=f"q{pick}")
            new_reason = e2.selectbox("Reason ", waste.ALLOWED_REASONS,
                                      index=waste.ALLOWED_REASONS.index(cur["reason"]), key=f"r{pick}")
            new_notes = e3.text_input("Notes ", value=cur.get("notes", ""),
                                      max_chars=waste.MAX_NOTES_LENGTH, key=f"n{pick}")
            b1, b2 = st.columns([1, 3])
            if b1.button("Update log"):
                res = waste.update_waste_log(pick, {"quantity": new_qty, "reason": new_reason,
                                                    "notes": new_notes}, donor_id=donor_id)
                st.session_state["flash"] = ("ok", "Log updated.") if res["ok"] else ("err", res["error"])
                st.rerun()
            confirm = b2.checkbox("Confirm delete")
            if b2.button("Delete log", disabled=not confirm):
                res = waste.delete_waste_log(pick, donor_id=donor_id)
                st.session_state["flash"] = ("ok", "Log deleted.") if res["ok"] else ("err", res["error"])
                st.rerun()
        note("In the sidebar, View as Donor limits changes to that donor's logs; "
             "View as Administrator can change any log.")

# ---------------------------------------------------------------- About
with tab_about:
    st.subheader("About this project")
    st.write("This application brings relational data (MySQL) and flexible document logs "
             "(MongoDB Atlas) into one interface, so surplus food, donations and waste can be "
             "analysed together.")
    st.markdown("""
| Layer | Technology | Responsibility |
|---|---|---|
| Interface | Streamlit (`app.py`) | Filters, charts, forms, role-based access |
| Structured data | MySQL (`db/mysql_conn.py`) | Donors, surplus, donations, collection records |
| Waste logs | MongoDB (`modules/waste.py`) | Validated CRUD, aggregation pipelines, CSV export |
| Link between them | `donor_id` | Joined in Python on the *Donated vs wasted* tab |
""")
    st.markdown("""
**Access control**

| Role | Can do |
|---|---|
| User | View all charts, tables and logs. No add, edit or delete. |
| Administrator | Everything a user can, plus add, edit and delete waste logs. Needs the password. |
""")
    st.write("Testing: run `python -m pytest -v` for the waste module tests (32 cases covering "
             "validation, ownership, aggregation totals, CSV export and database outages).")