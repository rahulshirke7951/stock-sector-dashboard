import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="Stock Dashboard", layout="wide")

st.title("📊 Sector Stock Dashboard")

folder = "dashboards"

if not os.path.exists(folder):
    st.error("No dashboards folder found. Run GitHub workflow first.")
    st.stop()

files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]

if not files:
    st.warning("No sector files generated yet.")
    st.stop()

selected_file = st.selectbox("Select Sector", files)
file_path = os.path.join(folder, selected_file)

prices = pd.read_excel(file_path, sheet_name="prices", index_col=0)
monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
summary = pd.read_excel(file_path, sheet_name="summary", index_col=0)

col1, col2 = st.columns([3, 1])

with col1:
    st.subheader("📈 Price Trend")
    fig = px.line(prices)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("📋 Performance Summary")
    st.dataframe(summary)

st.subheader("📊 Monthly Returns")
st.dataframe(monthly)
