import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

# Page Configuration
st.set_page_config(page_title="Stock Watchlist", layout="wide")

# UI DESIGN: Professional Header Styling & Table Centering
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; border-top: 4px solid #002b5b; }
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# Data Path Configuration
folder = "dashboards"
if not os.path.exists(folder):
    st.error(f"📂 Folder '{folder}' not found. Run engine.py first.")
    st.stop()

files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

# SIDEBAR: Control Panel
with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    # Load raw prices to build dynamic filters
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    # FEATURE: Dynamic Stock Multi-select
    all_stocks = sorted(prices_df.columns.tolist())
    selected_stocks = st.multiselect("Filter Stocks", all_stocks, default=all_stocks)
    
    # FEATURE: Dynamic Year Selection
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# LOGIC: Recalculate everything based on Sidebar selection
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Select stocks and years to display data.")
    st.stop()

# Dynamic CAGR and Absolute Return Math
days_diff = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_val = max(days_diff / 365.25, 0.1) # Prevent division by zero

summary_data = []
for s in selected_stocks:
    stock_series = filtered_prices[s].dropna()
    if len(stock_series) >= 2:
        start_p, end_p = stock_series.iloc[0], stock_series.iloc[-1]
        abs_ret = ((end_p / start_p) - 1) * 100
        cagr_val = (((end_p / start_p) ** (1 / years_val)) - 1) * 100
        summary_data.append({"Ticker": s, "Return %": abs_ret, "CAGR %": cagr_val, "Latest": end_p})

df_sum = pd.DataFrame(summary_data).sort_values("Return %", ascending=False)

# UI: HEADER & METRICS
clean_name = selected_file.replace(".xlsx", "")
st.title(f"📈 {clean_name}")
st.caption(f"📅 Active Period: {filtered_prices.index.min().date()} to {filtered_prices.index.max().date()}")

m1, m2 = st.columns(2)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.2f}%")
m2.metric("📅 Selection CAGR", "Avg Annualized", f"{df_sum['CAGR %'].mean():.2f}%")

st.divider()

# TABS: The 4 Analytical Views
t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Stats Table", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", 
                               color_continuous_scale='RdYlGn', template="simple_white"), use_container_width=True)
    with c2:
        st.subheader("Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="simple_white"), use_container_width=True)
    
    st.divider()
    st.subheader("🕵️ Rolling Consistency Check")
    try:
        # Load the pre-calculated rolling data
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        # Filter display for selected stocks/years without breaking the 1Y math
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="simple_white", labels={"value": "Rolling %"})
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except:
        st.info("Rolling data sheet syncing...")

with t2:
    # FEATURE: Styled Table with Centered Headers & 2-Decimal Precision
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
                 .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "{:.2f}"}), 
                 use_container_width=True, hide_index=True)
    
    # Download Report for the current view
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine='xlsxwriter') as writer:
        df_sum.to_excel(writer, index=False)
    st.download_button("📥 Export CSV/Excel Report", buf.getvalue(), f"{clean_name}_report.xlsx")

with t3:
    st.subheader("Monthly Returns (%)")
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    # Filter Heatmap Columns (Stocks) and Rows (Selected Years)
    f_m = m_data[selected_stocks]
    f_m = f_m[pd.to_datetime(f_m.index).year.isin(selected_years)]
    st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with t4:
    st.subheader("Quarterly Returns (%)")
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    # Filter Heatmap Columns (Stocks) and Rows (Selected Years)
    f_q = q_data[selected_stocks]
    f_q = f_q[f_q.index.str[:4].astype(int).isin(selected_years)]
    st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
