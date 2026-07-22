import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Initiative + Orange Weekly Dashboard", layout="wide")

DB_FILE = "media_data.db"

CHANNELS = ["Search", "IO Display", "Programmatic Display", "IO Video", "Programmatic Video", "Native"]
METRICS = ["Media Budget", "Impressions", "Clicks", "Conversions"]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            week_start TEXT,
            channel TEXT,
            metric TEXT,
            value REAL
        )
    """)
    conn.commit()
    conn.close()

def get_week_start(d):
    return d - pd.Timedelta(days=d.weekday())

def add_entry(week_start, channel, metric, value):
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO entries (week_start, channel, metric, value) VALUES (?, ?, ?, ?)",
        (str(week_start), channel, metric, value)
    )
    conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM entries", conn)
    conn.close()
    if not df.empty:
        df["week_start"] = pd.to_datetime(df["week_start"])
    return df

def delete_entry(entry_id):
    conn = sqlite3.connect(DB_FILE)
    conn.execute("DELETE FROM entries WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

init_db()

st.sidebar.title("Initiative + Orange Weekly Dashboard")
page = st.sidebar.radio("Navigate", ["Add Data", "Dashboard", "Manage Data"])

if page == "Add Data":
    st.title("Add Weekly Data")
    st.caption("Enter one row per channel/metric combination. Week is auto-set to the Monday of the selected date.")

    with st.form("entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            entry_date = st.date_input("Any date within the week", value=date.today())
            channel = st.selectbox("Channel", CHANNELS)
        with col2:
            metric = st.selectbox("Metric", METRICS)
            value = st.number_input("Value", min_value=0.0, step=1.0, format="%.2f")

        submitted = st.form_submit_button("Save Entry")
        if submitted:
            week_start = get_week_start(pd.Timestamp(entry_date))
            add_entry(week_start.date(), channel, metric, value)
            st.success(f"Saved: {channel} / {metric} = {value} for week of {week_start.date()}")

elif page == "Dashboard":
    st.title("Weekly overview for Orange Belgium")
    df = load_data()

    if df.empty:
        st.info("No data yet. Go to 'Add Data' to start logging data.")
    else:
        metric_filter = st.selectbox("Select metric to visualize", METRICS)
        filtered = df[df["metric"] == metric_filter]

        if filtered.empty:
            st.warning(f"No data logged for {metric_filter} yet.")
        else:
            col1, col2, col3 = st.columns(3)
            col1.metric(f"Total {metric_filter}", f"{filtered['value'].sum():,.2f}")
            col2.metric("Weeks logged", filtered["week_start"].nunique())
            col3.metric("Channels logged", filtered["channel"].nunique())

            st.subheader(f"Total {metric_filter} per Week")
            weekly = filtered.groupby("week_start")["value"].sum().reset_index()
            weekly = weekly.sort_values("week_start")
            st.bar_chart(weekly.set_index("week_start"))

            st.subheader(f"Total {metric_filter} per Channel")
            by_channel = filtered.groupby("channel")["value"].sum().reset_index()
            by_channel = by_channel.sort_values("value", ascending=False)
            st.bar_chart(by_channel.set_index("channel"))

            st.subheader("Detailed Table: Week x Channel")
            pivot = filtered.pivot_table(
                index="week_start", columns="channel", values="value", aggfunc="sum", fill_value=0
            )
            pivot.index = pivot.index.astype(str)
            st.dataframe(pivot, use_container_width=True)

elif page == "Manage Data":
    st.title("Manage Entries")
    df = load_data()
    if df.empty:
        st.info("No entries yet.")
    else:
        df_display = df.sort_values("week_start", ascending=False).copy()
        df_display["week_start"] = df_display["week_start"].dt.date
        st.dataframe(df_display, use_container_width=True)

        st.subheader("Delete an entry")
        entry_id = st.number_input("Entry ID to delete", min_value=0, step=1)
        if st.button("Delete"):
            delete_entry(int(entry_id))
            st.success(f"Deleted entry {entry_id}. Refresh the page to update the table.")
