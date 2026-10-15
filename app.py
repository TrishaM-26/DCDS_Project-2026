import streamlit as st
import pandas as pd
from db.mysql_conn import run_query
from modules.waste import waste_by_reason

st.title("Food Donation & Waste Dashboard")

st.header("From MySQL: Surplus Food Listings")
rows = run_query("SELECT food_name, quantity, unit, status FROM surplus_food", fetch=True)
if rows:
    st.dataframe(pd.DataFrame(rows))
else:
    st.error("Could not read from MySQL. Check .env and that MySQL is running.")

st.header("From MongoDB: Waste by Reason (kg)")
try:
    data = waste_by_reason()
    df = pd.DataFrame(data)
    st.bar_chart(df.set_index("reason")["total_kg"])
except Exception as e:
    st.error(f"MongoDB error: {e}")