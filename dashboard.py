import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
FOLDER            = "dashboards"
SHEET_PRICES      = "prices"
SHEET_METADATA    = "metadata"
SHEET_ROLLING_12M = "rolling_12m"
SHEET_MONTHLY     = "monthly_returns"
SHEET_QUARTERLY   = "quarterly_returns"

BRAND_DARK  = "#002b5b"
BRAND_MID   = "#004080"
BRAND_LIGHT = "#0066cc"

# ─────────────────────────────────────────────
# PAGE CONFIG & CSS
# ─────────────────────────────────────────────
st.set_page_config(page_title="Stock Watchlist Terminal", layout="wide")

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&family=DM+Mono&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
    .main-header {{ font-weight: 700; font-size: 2.6em; background: linear-gradient(135deg, {BRAND_DARK}, {BRAND_LIGHT}); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }}
    .info-chip {{ font-family: 'DM Mono', monospace; font-size: 0.8em; background: #f0f4fa; padding: 6px 14px; border-radius: 20px; border: 1px solid #d8e3f0; width: fit-content; margin: 0 auto; }}
    .stMetric {{ background: white; padding: 15px; border-radius: 12px; border-top: 4px solid {BRAND_DARK}; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# DATA LOADERS & HELPERS
# ─────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load_prices(path):
    df = pd.read_excel(path, sheet_name=SHEET_PRICES, index_col=0)
    df.index = pd.to_datetime(df.index)
    return df

@st.cache_data(show_spinner=False)
def load_meta(path):
    try:
        return pd.read_excel(path, sheet_name=SHEET_METADATA, index_col=0).iloc[:, 0].to_dict()
    except: return {}

@st.cache_data(show_spinner=False)
def load_sheet(path, sheet):
    try: return pd.read_excel(path, sheet_name=sheet, index_col=0)
    except: return None

def parse_quarterly_index(raw_index):
    parsed = []
    for x in raw_index:
        s = str(x).strip().upper()
        try:
            if "-" in s and len(s) >= 8: # YYYY-MM-DD
                parsed.append(pd.to_datetime(s).to_period("Q").to_timestamp())
            elif "Q" in s:
                s_norm = s.replace("-", "").replace(" ", "")
                if s_norm.startswith("Q"): # Q12024
                    q, y = int(s_norm[1]), int(s_norm[2:])
                else: # 2024Q1
                    y, q = int(s_norm[:4]), int(s_norm[5])
                parsed.append(pd.Timestamp(year=y, month=(q-1)*3+1, day=1))
            else: parsed.append(pd.to_datetime(s).to_period("Q").to_timestamp())
        except: parsed.append(pd.NaT)
    return pd.DatetimeIndex(parsed)

def calc_summary(df):
    rows = []
    for ticker in df.columns:
        col = df[ticker].dropna()
        if len(col) < 2: continue
        daily_ret = col.pct_change().dropna()
        yrs = max((col.index[-1] - col.index[0]).days / 365.25, 0.1)
        ret = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr = (((col.iloc[-1] / col.iloc[0]) ** (1/yrs)) - 1) * 100
        vol = daily_ret.std() * np.sqrt(252) * 100
        rows.append({"Ticker": ticker, "Return %": ret, "CAGR %": cagr, "Ann. Vol %": vol, "Sharpe": (cagr/vol if vol>0 else 0), "Latest": col.iloc[-1], "_yrs": yrs})
    return pd.DataFrame(rows).sort_values("Return %", ascending=False)

# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
if not os.path.exists(FOLDER):
    st.error(f"Folder '{FOLDER}' not found.")
    st.stop()

files = sorted([f for f in os.listdir(FOLDER) if f.endswith(".xlsx")])
with st.sidebar:
    st.title("📂 Watchlist Controls")
    sel_file = st.selectbox("Select Watchlist", files, on_change=st.cache_data.clear)
    path = os.path.join(FOLDER, sel_file)
    
    name_map = load_meta(path)
    prices_df = load_prices(path).rename(columns=name_map)
    
    all_stocks = sorted(prices_df.columns.tolist())
    sel_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks)
    
    yrs = sorted(prices_df.index.year.unique(), reverse=True)
    sel_yrs = st.multiselect("Years", yrs, default=yrs[:2])

if not sel_stocks or not sel_yrs:
    st.warning("Please select stocks and years.")
    st.stop()

filtered = prices_df[prices_df.index.year.isin(sel_yrs)][sel_stocks]
df_sum = calc_summary(filtered)

# ─────────────────────────────────────────────
# MAIN DASHBOARD
# ─────────────────────────────────────────────
st.markdown(f'<h1 class="main-header">📈 {sel_file.replace(".xlsx","")}</h1>', unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("🏆 Top Performer", f"{df_sum.iloc[0]['Return %']:.1f}%", df_sum.iloc[0]['Ticker'])
m2.metric("📈 Avg Return", f"{df_sum['Return %'].mean():.1f}%")
m3.metric("📅 Avg CAGR", f"{df_sum['CAGR %'].mean():.1f}%")
m4.metric("📉 Avg Volatility", f"{df_sum['Ann. Vol %'].mean():.1f}%")

t1, t2, t3, t4, t5 = st.tabs(["📊 Visuals", "📋 Stats", "📅 Monthly", "🏢 Quarterly", "🔍 Deep-Dive"])

# TAB 1: VISUALS
with t1:
    v1, v2 = st.columns([1, 1])
    with v1:
        st.subheader("Performance Ranking")
        fig = px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, use_container_width=True)
    with v2:
        st.subheader("Normalised Growth (Base 100)")
        norm = (filtered / filtered.bfill().iloc[0]) * 100
        st.plotly_chart(px.line(norm, template="plotly_white"), use_container_width=True)

# TAB 2: STATS
with t2:
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %", "Sharpe"], cmap="RdYlGn").format("{:.2f}"), use_container_width=True)

# TAB 3: MONTHLY
with t3:
    m_data = load_sheet(path, SHEET_MONTHLY)
    if m_data is not None:
        m_data = m_data.rename(columns=name_map)
        m_data.index = pd.to_datetime(m_data.index)
        f_m = m_data[m_data.index.year.isin(sel_yrs)][[s for s in sel_stocks if s in m_data.columns]]
        st.dataframe(f_m.sort_index(ascending=False).style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"), use_container_width=True)

# TAB 4: QUARTERLY (FIXED)
with t4:
    q_data = load_sheet(path, SHEET_QUARTERLY)
    if q_data is not None:
        q_data = q_data.rename(columns=name_map)
        q_data.index = parse_quarterly_index(q_data.index)
        avail = [s for s in sel_stocks if s in q_data.columns]
        if avail:
            f_q = q_data[q_data.index.year.isin(sel_yrs)][avail].sort_index(ascending=False)
            f_q.index = f_q.index.to_period("Q").astype(str)
            st.dataframe(f_q.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%", na_rep="—"), use_container_width=True)
        else: st.info("No stocks found in quarterly data.")
    else: st.info("Quarterly sheet missing.")

# TAB 5: DEEP-DIVE
with t5:
    target = st.selectbox("Select Stock", sel_stocks)
    s_data = filtered[target].dropna()
    full = prices_df[target].dropna()
    
    # Technical Indicators
    ma50 = full.rolling(50).mean().reindex(s_data.index)
    ma200 = full.rolling(200).mean().reindex(s_data.index)
    dd = (s_data / s_data.cummax() - 1) * 100
    
    fig_dd = px.area(dd, title=f"{target} Drawdown (%)", color_discrete_sequence=["#e74c3c"])
    st.plotly_chart(fig_dd, use_container_width=True)

    
    
    fig_main = go.Figure()
    fig_main.add_trace(go.Scatter(x=s_data.index, y=s_data, name="Price", line=dict(color=BRAND_DARK)))
    if not ma50.dropna().empty: fig_main.add_trace(go.Scatter(x=ma50.index, y=ma50, name="50 DMA", line=dict(dash="dot")))
    if not ma200.dropna().empty: fig_main.add_trace(go.Scatter(x=ma200.index, y=ma200, name="200 DMA", line=dict(dash="dash")))
    st.plotly_chart(fig_main, use_container_width=True)
