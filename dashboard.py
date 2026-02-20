import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="Sector Dashboard", layout="wide")

# Custom CSS for narrow columns
st.markdown("<style>div[data-testid='stDataFrame'] {width: fit-content;}</style>", unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

# ---------- Sidebar Controls ----------
with st.sidebar:
    st.title("🎯 Controls")
    selected_file = st.selectbox("Select Sector", files)
    file_path = os.path.join(folder, selected_file)

    # Load data for year extraction
    prices = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices.index = pd.to_datetime(prices.index)
    
    available_years = sorted(prices.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Filter Years", available_years, default=available_years)

# ---------- Data Loading ----------
summary = pd.read_excel(file_path, sheet_name="summary")
monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
quarterly = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)

# ---------- Header & Period Stamp ----------
sector_name = selected_file.replace(".xlsx", "").title()
start_date = prices.index.min().strftime('%d %b %Y')
end_date = prices.index.max().strftime('%d %b %Y')

st.title(f"📊 {sector_name} Analysis")
st.info(f"📅 **Data Period:** {start_date} to {end_date}")

# ---------- Metrics ----------
best_stock = summary.loc[summary["Total Return %"].idxmax()]
worst_stock = summary.loc[summary["Total Return %"].idxmin()]

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", f"{best_stock.iloc[0]}", f"{best_stock['Total Return %']:.2f}%")
m2.metric("📉 Worst Performer", f"{worst_stock.iloc[0]}", f"{worst_stock['Total Return %']:.2f}%", delta_color="inverse")
m3.metric("📈 Sector Avg", "Total Return", f"{summary['Total Return %'].mean():.2f}%")

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📋 Performance Summary", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap"])

with tab1:
    st.subheader("Performance Overview")
    # Column configuration for narrow width
    st.dataframe(
        summary.style.background_gradient(subset=["Total Return %"], cmap="RdYlGn"),
        use_container_width=False,
        column_config={"Unnamed: 0": "Ticker", "Start Price": {"format": "$%.2f"}, "Latest Price": {"format": "$%.2f"}}
    )

with tab2:
    st.subheader("Monthly Returns")
    # Filter heatmap by selected years
    filtered_m = monthly[monthly.index.str[:4].astype(int).isin(selected_years)]
    st.dataframe(filtered_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with tab3:
    st.subheader("Quarterly Returns")
    # Filter heatmap by selected years
    filtered_q = quarterly[quarterly.index.str[:4].astype(int).isin(selected_years)]
    st.dataframe(filtered_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
