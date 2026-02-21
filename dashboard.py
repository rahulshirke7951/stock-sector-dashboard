import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

st.set_page_config(page_title="Stock Watchlist", layout="wide", initial_sidebar_state="expanded")

# --- PREMIUM UI: Navy Blue Theme + Inter Font + Animations ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header { 
        font-family: 'Inter', sans-serif; font-weight: 700; font-size: 2.8em; 
        background: linear-gradient(135deg, #002b5b, #004080, #0066cc); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.5rem;
    }
    .timestamp { 
        font-family: 'Inter', sans-serif; font-weight: 500; color: #002b5b; text-align: center; font-size: 0.95em;
        background: linear-gradient(90deg, #f8f9ff, #e6e9ef); padding: 8px 16px; border-radius: 20px; 
        display: block; margin: 0 auto 20px auto; width: fit-content; border: 1px solid #e6e9ef;
    }
    .stMetric { 
        background: linear-gradient(145deg, #f8f9ff, #e6e9ef); padding: 20px; border-radius: 12px; 
        border: 1px solid #e6e9ef; border-top: 4px solid #002b5b; 
        box-shadow: 0 4px 8px rgba(0,43,91,0.1); transition: all 0.2s ease; 
    }
    .stMetric:hover { transform: translateY(-4px); box-shadow: 0 8px 20px rgba(0,43,91,0.2); }
    
    /* Centered Table Headers & Professional Data Cells */
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; font-family: 'Inter' !important; }
    td { text-align: center !important; font-family: 'Inter' !important; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.error("No data found. Please run engine.py.")
    st.stop()

# --- SIDEBAR: DYNAMIC CONTROLS ---
with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    # Load metadata (Real Names) first
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        name_map = meta_df.iloc[:, 0].to_dict()
    except:
        name_map = {}

    # Load Prices and Rename
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    prices_df.rename(columns=name_map, inplace=True)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    # SELECT ALL TOGGLE
    select_all = st.toggle("Select All Stocks", value=True)
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks if select_all else None)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# --- LOGIC LAYER ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Select stocks and years to view analytics.")
    st.stop()

# CAGR & Return Calculation
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

# --- DISPLAY LAYER ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
latest_date_str = prices_df.index.max().strftime('%d %b %Y')
st.markdown(f'<div class="timestamp">📅 Latest Data: {latest_date_str}</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.1f}%")
m2.metric("📈 Avg Return", f"{df_sum['Return %'].mean():.1f}%")
m3.metric("📅 Portfolio CAGR", f"{df_sum['CAGR %'].mean():.1f}%")

st.divider()

t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance Data", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("🔥 Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", 
                               color_continuous_scale='RdYlGn', template="plotly_white"), use_container_width=True)
    with c2:
        st.subheader("📈 Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="plotly_white"), use_container_width=True)
    
    st.divider()
    # ROLLING RETURNS (Restored)
    st.subheader("🕵️ Rolling 12M Consistency")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        roll.rename(columns=name_map, inplace=True)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("Rolling data sheet not found in Excel.")

with t2:
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
                 .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}), 
                 use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    try:
        m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        f_m = m_data[selected_stocks]
        f_m = f_m[f_m.index.year.isin(selected_years)]
        f_m.index = f_m.index.strftime('%Y-%b')
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("Monthly data syncing...")

with t4:
    st.subheader("Quarterly Returns (%)")
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        f_q = q_data[selected_stocks]
        f_q = f_q[f_q.index.year.isin(selected_years)]
        f_q.index = f_q.index.to_period('Q').astype(str)
        st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("Quarterly data syncing...")
