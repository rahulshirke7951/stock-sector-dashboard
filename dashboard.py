import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Stock Watchlist", layout="wide", initial_sidebar_state="expanded")

# Enhanced UI DESIGN: Professional Navy Blue Theme with Responsiveness
st.markdown("""
    <style>
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #e6e9ef; 
        border-top: 4px solid #002b5b; 
        box-shadow: 0 2px 4px rgba(0,43,91,0.1);
    }
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    .main-header { text-align: center; font-size: 2.5em; margin-bottom: 1rem; }
    .sidebar .stContainer { border: 1px solid #e6e9ef; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }
    @media (max-width: 768px) {
        .stPlotlyChart { height: 300px !important; }
        .main-header { font-size: 2em; }
    }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    if st.button("🔄 Reload Data"):
        st.rerun()
    
    # Load prices to build dynamic filters
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    all_stocks = sorted(prices_df.columns.tolist())

    st.write("---")
    
    # Grouped filters with containers
    with st.container(border=True):
        st.caption("Stocks")
        selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks, 
                                        help="Search and select multiple stocks (Ctrl+click)")
    
    with st.container(border=True):
        st.caption("Time Filter")
        available_years = sorted(prices_df.index.year.unique(), reverse=True)
        selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# Filter and Recalculate Logic
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Please select stocks and years to view analytics.")
    st.stop()

# Annualized CAGR Math
days_diff = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_val = max(days_diff / 365.25, 0.1)

summary = []
for s in selected_stocks:
    col = filtered_prices[s].dropna()
    if len(col) >= 2:
        ret = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr = (((col.iloc[-1] / col.iloc[0]) ** (1/years_val)) - 1) * 100
        summary.append({"Ticker": s, "Return %": ret, "CAGR %": cagr, "Latest": col.iloc[-1]})

df_sum = pd.DataFrame(summary).sort_values("Return %", ascending=False)
avg_cagr = df_sum['CAGR %'].mean()

# Header & Metrics in Container
header_container = st.container()
with header_container:
    st.markdown('<h1 class="main-header">📈 ' + selected_file.replace('.xlsx', '') + '</h1>', unsafe_allow_html=True)
    
    m1, m2 = st.columns(2)
    with m1:
        st.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.2f}%")
    with m2:
        st.metric("📅 Selection CAGR", f"{avg_cagr:.2f}%", "0.5%", delta_color="normal")  # Placeholder delta

st.divider()

# Tabs for Detailed Analysis
t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance Data", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 2])  # Adjusted ratio for better visuals
    with c1:
        st.subheader("Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', 
                              color="Return %", color_continuous_scale='RdYlGn', template="simple_white"), 
                       use_container_width=True)
    with c2:
        st.subheader("Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="simple_white"), use_container_width=True)
    
    st.divider()
    st.subheader("🕵️ Rolling Consistency (1Y Window)")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="simple_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: 
        st.info("Syncing rolling data...")

with t2:
    col_config = {
        "Return %": st.column_config.NumberColumn("Return %", format="%.2f%%"),
        "CAGR %": st.column_config.NumberColumn("CAGR %", format="%.2f%%"),
        "Latest": st.column_config.NumberColumn("Latest Price", format="%.2f")
    }
    with st.expander("View Full Performance Table", expanded=True):
        st.dataframe(df_sum, use_container_width=True, hide_index=True, column_config=col_config, height=400)

with t3:
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    m_data.index = pd.to_datetime(m_data.index)
    f_m = m_data[selected_stocks]
    f_m = f_m[f_m.index.year.isin(selected_years)]
    f_m.index = f_m.index.strftime('%Y-%b')
    with st.expander("Monthly Returns", expanded=True):
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                    use_container_width=True)

with t4:
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
    f_q = q_data[selected_stocks]
    f_q = f_q[f_q.index.year.isin(selected_years)]
    f_q.index = f_q.index.to_period('Q').astype(str)
    with st.expander("Quarterly Returns", expanded=True):
        st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                    use_container_width=True)
