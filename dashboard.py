import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Sector Stock Dashboard", layout="wide")

st.title("📊 Sector Stock Dashboard")

# ---------- Load Files ----------
folder = "dashboards"

if not os.path.exists(folder):
    st.error("No dashboards folder found. Run GitHub workflow first.")
    st.stop()

files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]

if not files:
    st.warning("No sector files generated yet.")
    st.stop()

# ---------- Sector Selection ----------
st.header("Sector Selection")

selected_file = st.selectbox("Choose Sector", files)
file_path = os.path.join(folder, selected_file)

try:
    summary = pd.read_excel(file_path, sheet_name="summary", index_col=0)
    cagr = pd.read_excel(file_path, sheet_name="cagr", index_col=0)
    monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
except:
    st.error("Could not read Excel file. Check sheets.")
    st.stop()

# ---------- Top Performer ----------
st.divider()
st.header("🏆 Performance Highlights")

if "Total Return %" in summary.columns:
    best_stock = summary["Total Return %"].idxmax()
    best_value = summary["Total Return %"].max()

    worst_stock = summary["Total Return %"].idxmin()
    worst_value = summary["Total Return %"].min()

    col1, col2 = st.columns(2)

    with col1:
        st.metric("🏆 Top Performer", best_stock, f"{best_value:.2f}%")

    with col2:
        st.metric("📉 Worst Performer", worst_stock, f"{worst_value:.2f}%")

# ---------- Summary + CAGR ----------
st.divider()
st.header("📋 Performance Overview")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Performance Summary")
    st.dataframe(summary, use_container_width=True)

with col2:
    st.subheader("CAGR")
    st.dataframe(cagr, use_container_width=True)

# ---------- Monthly Returns ----------
st.divider()
st.header("📊 Monthly Returns")

# color formatting
def highlight_returns(val):
    try:
        if val > 0:
            return "background-color:#c6efce"
        elif val < 0:
            return "background-color:#ffc7ce"
    except:
        pass
    return ""

styled_monthly = monthly.style.applymap(highlight_returns)

st.dataframe(styled_monthly, use_container_width=True)

# ---------- Sector Ranking ----------
st.divider()
st.header("📊 Sector Ranking")

if "Total Return %" in summary.columns:
    ranking = summary.sort_values("Total Return %", ascending=False)
    st.dataframe(ranking, use_container_width=True)
