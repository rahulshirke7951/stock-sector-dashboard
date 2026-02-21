import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO
from datetime import datetime

st.set_page_config(page_title="Stock Watchlist", layout="wide", initial_sidebar_state="expanded")

# --- ENHANCED UI: Premium Navy Blue Theme ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header { 
        font-weight: 700; font-size: 2.8em; 
        background: linear-gradient(135deg, #002b5b, #004080, #0066cc); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.2rem;
    }
    .timestamp { 
        font-weight: 500; color: #002b5b; text-align: center; font-size: 0.9em;
        background: #f0f2f6; padding: 5px 15px; border-radius: 20px; 
        display: block; margin: 0 auto 20px auto; width: fit-content;
    }
    .stMetric { 
        background: #ffffff; padding: 20px; border-radius: 12px; 
        border: 1px solid #e6e9ef; border-top: 4px solid #002b5b; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    /* Fixed Table Headers & Alignment */
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ACCESS LAYER ---
folder = "dashboards"
if not os.path.exists(folder):
    st.error(f"Folder '{folder}' not found. Please run engine.py first.")
    st.stop()

files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

# --- SIDEBAR: DYNAMIC CONTROLS ---
with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    # Cache data for speed
    @st.cache_data
    def load_prices(path):
        df = pd.read_excel(path, sheet_name="prices", index_col=0)
        df.index = pd.to_datetime(df.index)
        return df

    prices_df = load_prices(file_path)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    # RESTORED: Select All Toggle
    select_all = st.toggle("Select All Stocks", value=True)
    if select_all:
        selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks)
    else:
        selected_stocks = st.multiselect("Active Stocks", all_stocks)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# --- LOGIC LAYER ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Please select stocks and years to view analytics.")
    st.stop()

# Performance Calculations
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

# --- PRESENTATION LAYER ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
st.markdown(f'<div class="timestamp">📅 Period: {filtered_prices.index.min().date()} to {filtered_prices.index.max().date()}</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.1f}%")
m2.metric("📈 Avg Return", f"{df_sum['Return %'].mean():.1f}%")
m3.metric("📅 Selection CAGR", f"{df_sum['CAGR %'].mean():.1f}%")

st.divider()

t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance Data", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("🔥 Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", 
                               color_continuous_scale='RdYlGn', template="simple_white"), use_container_width=True)
    with c2:
        st.subheader("📈 Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="simple_white"), use_container_width=True)
    
    st.divider()
    st.subheader("🕵️ Rolling 12M Returns")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="simple_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("Rolling data syncing...")

with t2:
    # Centered and formatted table
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
                 .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}), 
                 use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    m_data.index = pd.to_datetime(m_data.index)
    f_m = m_data[selected_stocks]
    f_m = f_m[f_m.index.year.isin(selected_years)]
    # RESTORED: Proper Month-Year Indexing
    f_m.index = f_m.index.strftime('%Y-%b')
    st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with t4:
    st.subheader("Quarterly Returns (%)")
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    # Safe date conversion
    q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
    f_q = q_data[selected_stocks]
    f_q = f_q[f_q.index.year.isin(selected_years)]
    # RESTORED: Proper Quarter Labeling
    f_q.index = f_q.index.to_period('Q').astype(str)
    st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
