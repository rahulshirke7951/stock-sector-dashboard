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
    st.error(f"🚨 Folder '{folder}' not found.")
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
    # ROLLING YEAR LOGIC
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
else: start_date = pd.to_datetime(f"{min(selected_years) if selected_years else 2000}-01-01")

if horizon == "Custom Years":
    filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]
else:
    filtered_prices = prices_df.loc[start_date:][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ No data found.")
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

# --- HEADER ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

c_inf1, c_inf2, c_inf3 = st.columns(3)
with c_inf1: st.markdown(f'<div class="timestamp">📅 <b>Period:</b> {filtered_prices.index.min().strftime("%d %b %Y")} — {filtered_prices.index.max().strftime("%d %b %Y")}</div>', unsafe_allow_html=True)
with c_inf2: st.markdown(f'<div class="timestamp">📊 <b>Days:</b> {len(filtered_prices)} Sessions</div>', unsafe_allow_html=True)
with c_inf3: st.markdown(f'<div class="timestamp">🔄 <b>Last Sync:</b> {sync_time}</div>', unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", f"{df_sum.iloc[0]['Return %']:.1f}%", f"Stock: {df_sum.iloc[0]['Ticker']}")
m2.metric("📈 Selection Avg Return", f"{df_sum['Return %'].mean():.1f}%", "Overall Portfolio")
m3.metric("📅 Annualized CAGR", f"{df_sum['CAGR %'].mean():.1f}%", f"Over {years_val:.1f} Years")

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Visuals", "📋 Stats", "📅 Monthly", "🏢 Quarterly", "📆 Daily", "🔍 Deep-Dive"])

with t1:

    v_col1, v_col2 = st.columns([1, 1.5])
    with v_col1:
        st.subheader("🔥 Performance Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="plotly_white"), use_container_width=True)
    with v_col2:
        st.subheader("📈 Relative Price Movement")
        st.plotly_chart(px.line(filtered_prices, template="plotly_white"), use_container_width=True)
 

    
    st.divider()
    st.subheader("🕵️ Rolling 12M Return Consistency")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        roll.rename(columns=name_map, inplace=True)
        display_roll = roll.loc[filtered_prices.index.min():filtered_prices.index.max(), selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("ℹ️ Rolling analysis unavailable for this window.")

with t2:
    st.subheader("Detailed Performance Metrics")
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn").format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}), use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    try:
        m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        # Slicing based on years present in current selection
        active_years = filtered_prices.index.year.unique()
        f_m = m_data[m_data.index.year.isin(active_years)][selected_stocks]
        f_m = f_m.sort_index(ascending=False)
        f_m.index = f_m.index.strftime('%Y-%b')
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("ℹ️ Monthly data not found.")

with t4:
    st.subheader("Quarterly Returns (%)")
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        active_years = filtered_prices.index.year.unique()
        f_q_final = q_data[q_data.index.year.isin(active_years)][selected_stocks]
        f_q_final = f_q_final.sort_index(ascending=False)
        f_q_final.index = f_q_final.index.to_period('Q').astype(str)
        st.dataframe(f_q_final.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("ℹ️ Quarterly data not found.")

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
    st.error(f"🚨 Folder '{folder}' not found.")
    st.stop()

files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

# --- SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select Watchlist", files, key="main_watchlist_selector")
    file_path = os.path.join(folder, selected_file)
    
    if st.button("🔄 Reload & Sync Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Load metadata
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        name_map = meta_df.iloc[:, 0].to_dict()
    except: name_map = {}

    # Load Prices
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
else: start_date = pd.to_datetime(f"{min(selected_years) if selected_years else 2000}-01-01")

if horizon == "Custom Years":
    filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]
else:
    filtered_prices = prices_df.loc[start_date:][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ No data found. Adjust your filters.")
    st.stop()

# Overall CAGR Calculations
days_diff = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_val = max(days_diff / 365.25, 0.1)
summary_list = []
for s in selected_stocks:
    col = filtered_prices[s].dropna()
    if len(col) >= 2:
        ret = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr = (((col.iloc[-1] / col.iloc[0]) ** (1/years_val)) - 1) * 100
        summary_list.append({"Ticker": s, "Return %": ret, "CAGR %": cagr, "Latest": col.iloc[-1]})
df_sum = pd.DataFrame(summary_list).sort_values("Return %", ascending=False)

# --- HEADER ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

c_inf1, c_inf2, c_inf3 = st.columns(3)
with c_inf1: st.markdown(f'<div class="timestamp">📅 <b>Period:</b> {filtered_prices.index.min().strftime("%d %b %Y")} — {filtered_prices.index.max().strftime("%d %b %Y")}</div>', unsafe_allow_html=True)
with c_inf2: st.markdown(f'<div class="timestamp">📊 <b>Days:</b> {len(filtered_prices)} Sessions</div>', unsafe_allow_html=True)
with c_inf3: st.markdown(f'<div class="timestamp">🔄 <b>Last Sync:</b> {sync_time}</div>', unsafe_allow_html=True)

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Visuals", "📋 Stats", "📅 Monthly", "🏢 Quarterly", "📆 Daily Analysis", "🔍 Deep-Dive"])

with t5:
    # --- 1. SELECTION UI ---
    available_months = sorted(filtered_prices.index.strftime('%Y-%m').unique().tolist(), reverse=True)
    sel_months = st.multiselect("📅 Select Month(s) to Analyze", available_months, default=available_months[:1], key="d_month")

    if sel_months:
        # --- 2. CALCULATE RETURNS FOR PERIOD ---
        daily_ret_full = prices_df.pct_change() * 100
        target_indices = prices_df[prices_df.index.strftime('%Y-%m').isin(sel_months)].index
        day_view = daily_ret_full.loc[target_indices, selected_stocks].copy()

        # --- 3. DYNAMIC PERFORMANCE SUMMARY (THE MISSING PIECE) ---
        period_summary = pd.DataFrame({
            'Total Return (%)': day_view.sum(),
            'Best Day (%)': day_view.max(),
            'Worst Day (%)': day_view.min(),
            'Avg Daily Move (%)': day_view.mean()
        }).sort_values(by='Total Return (%)', ascending=False)

        # Top 2 Winners for Auto-Selection in Chart
        top_2_names = period_summary.head(2).index.tolist()

        # --- 4. INSIGHT TILES ---
        st.subheader("🏁 Period Highlights")
        i_col1, i_col2, i_col3 = st.columns(3)
        i_col1.metric("🥇 Period Leader", f"{period_summary.iloc[0]['Total Return (%)']:.2f}%", f"{period_summary.index[0]}")
        i_col2.metric("🚀 Top Daily Move", f"{day_view.max().max():.2f}%", f"{day_view.max().idxmax()}")
        i_col3.metric("📉 Deepest Day Cut", f"{day_view.min().min():.2f}%", f"{day_view.min().idxmin()}")

        # --- 5. PERFORMANCE SUMMARY TABLE ---
        st.write("### 📊 Performance Ranking for Selected Period")
        st.dataframe(period_summary.style.background_gradient(cmap='YlGn', subset=['Total Return (%)']).format("{:.2f}%"), use_container_width=True)

        st.divider()

        # --- 6. UNIFIED TREND CHART & FILTERS ---
        chart_col, ctrl_col = st.columns([4, 1])
        with ctrl_col:
            st.write("🔍 **Chart Filters**")
            sel_stocks_chart = st.multiselect("Select Stocks:", selected_stocks, default=top_2_names, key=f"chart_select_{sel_months}")
            st.caption("Period winners are auto-selected.")

        with chart_col:
            if sel_stocks_chart:
                st.subheader("🕵️ Performance Trend (Cumulative Growth %)")
                cum_trend = ((1 + day_view[sel_stocks_chart] / 100).cumprod() - 1) * 100
                fig_trend = px.line(cum_trend, template="plotly_white", markers=True, height=450)
                fig_trend.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig_trend, use_container_width=True)

        # --- 7. DAILY HEATMAP ---
        st.subheader("📋 Daily Returns Detail (%)")
        st.dataframe(day_view.sort_index(ascending=False).style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

        # --- 8. CSV DOWNLOAD ---
        st.divider()
        csv_data = filtered_prices.to_csv().encode('utf-8')
        st.download_button(label="📥 Download Price History (CSV)", data=csv_data, file_name="stock_data.csv", mime='text/csv', use_container_width=True)


with t6:
    st.subheader("🔍 Individual Stock Deep-Dive")
    target_stock = st.selectbox("Pick a stock:", selected_stocks, key="dd_ticker")
    if target_stock:
        s_data = filtered_prices[target_stock].dropna()
        full_p = prices_df[target_stock].dropna()
        ma50 = full_p.rolling(50).mean().loc[s_data.index]
        ma200 = full_p.rolling(200).mean().loc[s_data.index]
        
        if ma50.iloc[-1] > ma200.iloc[-1]: st.success("🚀 Golden Cross (Bullish)")
        else: st.error("⚠️ Death Cross (Bearish)")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"₹{s_data.iloc[-1]:.2f}")
        c2.metric("Period Return", f"{((s_data.iloc[-1]/s_data.iloc[0])-1)*100:.2f}%")
        c3.metric("Peak Price", f"₹{s_data.max():.2f}")
        dd = (s_data / s_data.cummax() - 1) * 100
        c4.metric("Max Drawdown", f"{dd.min():.2f}%")

        fig_main = px.line(s_data, template="plotly_white")
        fig_main.add_scatter(x=ma50.index, y=ma50, name="50 DMA", line=dict(dash='dash', color='orange'))
        fig_main.add_scatter(x=ma200.index, y=ma200, name="200 DMA", line=dict(dash='dot', color='red'))
        st.plotly_chart(fig_main, use_container_width=True)

        cl, cr = st.columns(2)
        cl.plotly_chart(px.area(dd, title="Drawdown %", template="plotly_white", color_discrete_sequence=['red']), use_container_width=True)
        cr.plotly_chart(px.histogram(s_data.pct_change()*100, nbins=30, title="Return Distribution", template="plotly_white"), use_container_width=True)
