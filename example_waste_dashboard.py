"""
EXAMPLE ONLY - how the dashboard can use modules/waste.py.

This file is a reference for whoever builds the Streamlit dashboard.  Copy what
is useful, or call render_waste_section() from the dashboard page.  Nothing in
the waste module depends on this file.

    donor_id=None  -> admin view (all donors)
    donor_id=<n>   -> donor view (only that donor's logs; edits are limited too)
"""
import pandas as pd
import streamlit as st

from modules import waste


def render_waste_section(donor_id=None):
    """Draw the whole waste section; shows a friendly message if MongoDB is down."""
    try:
        _log_form(donor_id)
        _tables_and_charts(donor_id)
        if donor_id is None:
            _alert()
    except waste.WasteDBError as exc:      # queries raise this when the DB is unreachable
        st.error(str(exc))


def _log_form(donor_id):
    st.subheader("Log waste")
    with st.form("log_waste_form", clear_on_submit=True):
        if donor_id is None:
            chosen_donor = st.selectbox("Donor", list(waste.VALID_DONOR_IDS))
        else:
            chosen_donor = donor_id
        category_id = st.selectbox("Category", list(waste.CATEGORIES),
                                   format_func=waste.CATEGORIES.get)
        item = st.text_input("Item")
        quantity = st.number_input("Quantity", min_value=0.1, value=1.0, step=0.5)
        unit = st.selectbox("Unit", list(waste.KG_PER_UNIT))
        reason = st.selectbox("Reason", waste.ALLOWED_REASONS)
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Save")
    if submitted:
        # Commands never raise for user mistakes: check result["ok"].
        result = waste.log_waste(chosen_donor, category_id, item, quantity, unit,
                                 reason, notes=notes or None)
        if result["ok"]:
            st.success(f"Saved ({result['qty_kg']} kg).")
        else:
            st.error(result["error"])


def _tables_and_charts(donor_id):
    st.subheader("Recent logs")
    logs = waste.get_waste_logs(donor_id=donor_id, limit=50)
    if logs:
        st.dataframe(pd.DataFrame(logs).drop(columns=["id"]), hide_index=True)
        st.download_button("Download CSV", waste.waste_logs_to_csv_text(logs),
                           "waste_logs.csv", "text/csv")
    else:
        st.info("No waste logged yet.")

    st.subheader("Waste by reason (kg)")
    by_reason = waste.waste_by_reason(donor_id=donor_id)
    if by_reason:
        st.bar_chart(pd.DataFrame(by_reason).set_index("reason")["total_kg"])

    st.subheader("Waste by month (kg)")
    by_month = waste.waste_by_month(donor_id=donor_id)
    if by_month:
        st.line_chart(pd.DataFrame(by_month).set_index("month")["total_kg"])


def _alert():
    st.subheader("High-waste alert")
    threshold = st.number_input("Alert threshold (kg)", min_value=0.0,
                                value=float(waste.HIGH_WASTE_KG))
    flagged = waste.high_waste_donors(threshold)
    if not flagged:
        st.info("No donor has reached the threshold.")
    for row in flagged:
        st.warning(f"Donor {row['donor_id']} has wasted {row['total_kg']} kg "
                   f"in {row['logs']} logs.")
