import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime
import io

# --- CONFIGURATION & PAGE SETUP ---
st.set_page_config(page_title="Stock Watchlist Terminal", layout="wide", initial_sidebar_state="expanded")

# --- PREMIUM UI CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main-header { 
        font-family: 'Inter', sans-serif; font-weight: 700; font-size: 2.8em; 
        background: linear-gradient(135deg, #002b5b, #004080, #0066cc); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        text-align: center; margin-bottom: 0.2rem;
    }
    .timestamp { 
        font-family: 'Inter', sans-serif; font-weight: 500; color: #002b5b; text-align: center; font-size: 0.85em;
        background: #f0f2f6; padding: 6px 12px; border-radius: 15px; 
        display: block; margin: 0 auto; width: fit-content; border: 1px solid #e6e9ef;
    }
    .stMetric { 
        background: white; padding: 20px; border-radius: 12px; 
        border: 1px solid #e6e9ef; border-top: 4px solid #002b5b; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
if not os.path.exists(folder):
    st.error(f"🚨 Folder '{folder}' not found. Please run your engine script first.")
    st.stop()

files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select Watchlist", files)
    file_path = os.path.join(folder, selected_file)
    
    if st.button("🔄 Reload & Sync Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Load metadata and prices
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        name_map = meta_df.iloc[:, 0].to_dict()
    except: name_map = {}

    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    prices_df.rename(columns=name_map, inplace=True)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    select_all = st.toggle("Select All Stocks", value=True)
    current_default = all_stocks if select_all else []
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=current_default)

    st.markdown("---")
    horizon = st.radio("⏱️ Time Horizon", ["Last 12 Months", "Last 6 Months", "Last 3 Months", "All Time", "Custom Years"], index=0)
    
    selected_years = []
    if horizon == "Custom Years":
        available_years = sorted(prices_df.index.year.unique(), reverse=True)
        selected_years = st.multiselect("Select Years", available_years, default=available_years[:1])

# --- LOGIC LAYER ---
latest_date = prices_df.index.max()
if horizon == "Last 12 Months": start_date = latest_date - pd.DateOffset(months=12)
elif horizon == "Last 6 Months": start_date = latest_date - pd.DateOffset(months=6)
elif horizon == "Last 3 Months": start_date = latest_date - pd.DateOffset(months=3)
elif horizon == "All Time": start_date = prices_df.index.min()
else: start_date = pd.to_datetime(f"{min(selected_years)}-01-01")

if horizon == "Custom Years":
    filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]
else:
    filtered_prices = prices_df.loc[start_date:][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ No data found. Adjust your filters.")
    st.stop()

# CAGR Calculations
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

# --- NEW: SIDEBAR DOWNLOAD BUTTON ---
with st.sidebar:
    st.markdown("---")
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_sum.to_excel(writer, index=False, sheet_name='Performance_Report')
    excel_data = output.getvalue()
    st.download_button(label="📥 Download Excel Report", data=excel_data, file_name=f"Report_{selected_file}", mime="application/vnd.ms-excel", use_container_width=True)

# --- MAIN UI ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

c_inf1, c_inf2, c_inf3 = st.columns(3)
with c_inf1: st.markdown(f'<div class="timestamp">📅 <b>Period:</b> {filtered_prices.index.min().strftime("%d %b %Y")} — {filtered_prices.index.max().strftime("%d %b %Y")}</div>', unsafe_allow_html=True)
with c_inf2: st.markdown(f'<div class="timestamp">📊 <b>Days:</b> {len(filtered_prices)} Trading Sessions</div>', unsafe_allow_html=True)
with c_inf3: st.markdown(f'<div class="timestamp">🔄 <b>Last Sync:</b> {sync_time}</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", f"{df_sum.iloc[0]['Return %']:.1f}%", f"Stock: {df_sum.iloc[0]['Ticker']}")
m2.metric("📈 Selection Avg Return", f"{df_sum['Return %'].mean():.1f}%", "Overall Portfolio")
m3.metric("📅 Annualized CAGR", f"{df_sum['CAGR %'].mean():.1f}%", f"Over {years_val:.1f} Years")

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Visuals", "📋 Stats", "📅 Monthly", "🏢 Quarterly", "📆 Daily", "🔍 Deep-Dive"])

with t1:
    col_v1, col_v2 = st.columns([1, 1.5])
    with col_v1: st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="plotly_white", title="Ranking"), use_container_width=True)
    with col_v2: st.plotly_chart(px.line(filtered_prices, template="plotly_white", title="Price Movement"), use_container_width=True)
    
    st.subheader("🕵️ Rolling 12M Consistency")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        roll.rename(columns=name_map, inplace=True)
        display_roll = roll.loc[filtered_prices.index.min():filtered_prices.index.max(), selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("Rolling data unavailable for this window.")

with t2:
 
# Create a dictionary for specific column formatting
st.dataframe(
    df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
    .format({
        "Return %": "{:.2f}%", 
        "CAGR %": "{:.2f}%", 
        "Latest": "₹{:.2f}"
    }), 
    use_container_width=True, 
    hide_index=True
)


with t3:
    try:
        m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        f_m = m_data.loc[filtered_prices.index.min():filtered_prices.index.max(), selected_stocks]
        f_m.index = f_m.index.strftime('%Y-%b')
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("Monthly data not available.")

with t4:
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        f_q_final = q_data.loc[filtered_prices.index.min():filtered_prices.index.max(), selected_stocks]
        f_q_final.index = f_q_final.index.to_period('Q').astype(str)
        st.dataframe(f_q_final.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("Quarterly data not available.")

with t5:
    available_months = sorted(filtered_prices.index.strftime('%Y-%m').unique().tolist(), reverse=True)
    sel_months = st.multiselect("📅 Select Month(s)", available_months, default=available_months[:1])
    if sel_months:
        day_view = (prices_df.pct_change() * 100).loc[prices_df[prices_df.index.strftime('%Y-%m').isin(sel_months)].index, selected_stocks]
        st.dataframe(day_view.sort_index(ascending=False).style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with t6:
    target_stock = st.selectbox("Deep-Dive Stock:", selected_stocks)
    if target_stock:
        s_data = filtered_prices[target_stock].dropna()
        full_p = prices_df[target_stock].dropna()
        ma50 = full_p.rolling(50).mean().loc[s_data.index]
        ma200 = full_p.rolling(200).mean().loc[s_data.index]
        
        if ma50.iloc[-1] > ma200.iloc[-1]: st.success("🚀 Golden Cross Active")
        else: st.error("⚠️ Death Cross Active")
        
        st.plotly_chart(px.line(s_data, template="plotly_white").add_scatter(x=ma50.index, y=ma50, name="50 DMA").add_scatter(x=ma200.index, y=ma200, name="200 DMA"), use_container_width=True)
