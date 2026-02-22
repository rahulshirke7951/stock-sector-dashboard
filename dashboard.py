import streamlit as st
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

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
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); transition: all 0.2s ease; 
    }
    .stMetric:hover { transform: translateY(-3px); box-shadow: 0 8px 15px rgba(0,0,0,0.1); }
    
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
    
    # 🔄 RELOAD BUTTON (Clears Cache)
    if st.button("🔄 Reload & Sync Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    # Load metadata (Mapping Tickers to Long Names)
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        name_map = meta_df.iloc[:, 0].to_dict()
    except:
        name_map = {}

    # Load Price Data
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    prices_df.rename(columns=name_map, inplace=True)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    # SELECT ALL TOGGLE
    select_all = st.toggle("Select All Stocks", value=True)
    selected_stocks = st.multiselect("Active Stocks", all_stocks, 
                                     default=all_stocks if select_all else None)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# --- LOGIC LAYER ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Please adjust your sidebar filters to display data.")
    st.stop()

# CAGR & Total Return Calculations
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

# --- HEADER & CONTEXTUAL INFO ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)

# Context Bar Variables
start_dt = filtered_prices.index.min().strftime('%d %b %Y')
end_dt = filtered_prices.index.max().strftime('%d %b %Y')
trade_days = len(filtered_prices)
sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

c_inf1, c_inf2, c_inf3 = st.columns(3)
with c_inf1:
    st.markdown(f'<div class="timestamp">📅 <b>Period:</b> {start_dt} — {end_dt}</div>', unsafe_allow_html=True)
with c_inf2:
    st.markdown(f'<div class="timestamp">📊 <b>Days:</b> {trade_days} Trading Sessions</div>', unsafe_allow_html=True)
with c_inf3:
    st.markdown(f'<div class="timestamp">🔄 <b>Last Sync:</b> {sync_time}</div>', unsafe_allow_html=True)

st.write("") 

# Metrics
m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.1f}%")
m2.metric("📈 Selection Avg Return", f"{df_sum['Return %'].mean():.1f}%")
m3.metric("📅 Annualized CAGR", f"{df_sum['CAGR %'].mean():.1f}%")

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["📊 Visuals", "📋 Performance Stats", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap","📆 Daily Heatmap"])

with t1:
    v_col1, v_col2 = st.columns([1, 1.5])
    with v_col1:
        st.subheader("🔥 Performance Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', 
                               color="Return %", color_continuous_scale='RdYlGn', 
                               template="plotly_white"), use_container_width=True)
    with v_col2:
        st.subheader("📈 Relative Price Movement")
        st.plotly_chart(px.line(filtered_prices, template="plotly_white"), use_container_width=True)
    
    st.divider()
    # ROLLING 12M CHART
    st.subheader("🕵️ Rolling 12M Return Consistency")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        roll.rename(columns=name_map, inplace=True)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except:
        st.info("ℹ️ Rolling analysis unavailable. Run engine.py to sync.")

with t2:
    st.subheader("Detailed Performance Metrics")
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
    except:
        st.info("ℹ️ Monthly data not found in Excel.")

with t4:
    st.subheader("Quarterly Returns (%)")
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        # Logic fix: assign variable first
        f_q_data = q_data[selected_stocks]
        f_q_final = f_q_data[f_q_data.index.year.isin(selected_years)]
        f_q_final.index = f_q_final.index.to_period('Q').astype(str)
        st.dataframe(f_q_final.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except:
        st.info("ℹ️ Quarterly data not found in Excel.")

with t5:
    # 1. Selection UI - Filtered by the years you picked in the sidebar
    available_months = sorted(
        prices_df[prices_df.index.year.isin(selected_years)].index.strftime('%Y-%m').unique().tolist(), 
        reverse=True
    )
    
    # Default to the most recent month
    default_month = [available_months[0]] if available_months else []

    # Dropdown to select months
    sel_months = st.multiselect(
        "📅 Select Month(s) to Analyze", 
        available_months, 
        default=default_month, 
        key="daily_view_multi"
    )

    st.divider()

    try:
        # 2. Logic: Prepare the daily data
        daily_ret = filtered_prices.pct_change() * 100
        day_view = daily_ret[daily_ret.index.strftime('%Y-%m').isin(sel_months)].copy()
        
        if not day_view.empty:
            # --- SMART LOGIC: Find Top 2 Performers for these specific months ---
            # It adds up all daily moves to see who grew the most
            month_totals = day_view.sum().sort_values(ascending=False)
            top_2_names = month_totals.head(2).index.tolist()
            
            # 3. Stock Selector for Chart (Pre-filled with the Top 2 winners)
            sel_stocks_chart = st.multiselect(
                "🔍 Filter Stocks for Trend Chart", 
                selected_stocks, 
                default=top_2_names, 
                key="d_stock"
            )

            # --- INSIGHT METRICS (Best/Worst Day) ---
            max_val = day_view.max().max()
            min_val = day_view.min().min()
            
            best_stock = day_view.max().idxmax()
            best_date = day_view[best_stock].idxmax().strftime('%d %b')
            
            worst_stock = day_view.min().idxmin()
            worst_date = day_view[worst_stock].idxmin().strftime('%d %b')

            m_col1, m_col2 = st.columns(2)
            m_col1.metric(f"🚀 Top Move ({best_stock})", f"{max_val:.2f}%", f"on {best_date}")
            m_col2.metric(f"📉 Deepest Cut ({worst_stock})", f"{min_val:.2f}%", f"on {worst_date}")

            # --- VISUAL TREND (Line Chart) ---
            if sel_stocks_chart:
                st.subheader("🕵️ Daily Volatility Trend")
                fig_daily = px.line(
                    day_view[sel_stocks_chart], 
                    template="plotly_white", 
                    labels={"value": "Return %", "index": "Date"},
                    markers=True
                )
                fig_daily.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
                fig_daily.update_layout(hovermode="x unified")
                st.plotly_chart(fig_daily, use_container_width=True)
            else:
                st.warning("Please select at least one stock to view the chart.")

            # --- DETAILED HEATMAP (The Table) ---
            st.subheader("📋 Daily Returns Detail (%)")
            table_display = day_view.copy()
            table_display.index = table_display.index.strftime('%Y-%m-%d (%a)')
            
            st.dataframe(
                table_display.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                use_container_width=True
            )
            
            st.caption(f"Analysis covers {len(day_view)} trading sessions based on your selections.")
        else:
            st.info("Please select at least one month that matches your Sidebar Year filter.")
            
    except Exception as e:
        st.error(f"Error in Daily View: {e}")
