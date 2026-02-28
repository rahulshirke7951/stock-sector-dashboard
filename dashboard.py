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
    selected_file = st.selectbox("Select Watchlist", files, key="main_file_select")
    file_path = os.path.join(folder, selected_file)
    
    if st.button("🔄 Reload & Sync Data", use_container_width=True, key="sync_button"):
        st.cache_data.clear()
        st.rerun()

    # Load metadata
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        name_map = meta_df.iloc[:, 0].to_dict()
    except: name_map = {}

    # Load Price Data
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    prices_df.rename(columns=name_map, inplace=True)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    select_all = st.toggle("Select All Stocks", value=True, key="toggle_all")
    current_default = all_stocks if select_all else []
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=current_default, key="stock_selector")

    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2], key="year_selector")

# --- LOGIC LAYER ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Please adjust your sidebar filters to display data.")
    st.stop()

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

# --- HEADER & CONTEXT BAR ---
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime('%Y-%m-%d %H:%M')

c_inf1, c_inf2, c_inf3 = st.columns(3)
with c_inf1: st.markdown(f'<div class="timestamp">📅 <b>Period:</b> {filtered_prices.index.min().strftime("%d %b %Y")} — {filtered_prices.index.max().strftime("%d %b %Y")}</div>', unsafe_allow_html=True)
with c_inf2: st.markdown(f'<div class="timestamp">📊 <b>Days:</b> {len(filtered_prices)} Trading Sessions</div>', unsafe_allow_html=True)
with c_inf3: st.markdown(f'<div class="timestamp">🔄 <b>Last Sync:</b> {sync_time}</div>', unsafe_allow_html=True)

# Main Metrics
m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", f"{df_sum.iloc[0]['Return %']:.1f}%", f"Stock: {df_sum.iloc[0]['Ticker']}")
m2.metric("📈 Selection Avg Return", f"{df_sum['Return %'].mean():.1f}%", "Overall Portfolio")
m3.metric("📅 Annualized CAGR", f"{df_sum['CAGR %'].mean():.1f}%", f"Over {years_val:.1f} Years")

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Visuals", "📋 Performance Stats", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap","📆 Daily Heatmap","🔍 Individual Stock Deep-Dive"])

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
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("ℹ️ Rolling analysis unavailable. Run engine.py to sync.")

with t2:
    st.subheader("Detailed Performance Metrics")
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn").format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}), use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    try:
        m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        f_m = m_data[selected_stocks]
        f_m = f_m[f_m.index.year.isin(selected_years)].sort_index(ascending=False)
        f_m.index = f_m.index.strftime('%Y-%b')
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("ℹ️ Monthly data not found.")

with t4:
    st.subheader("Quarterly Returns (%)")
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        f_q_final = q_data[selected_stocks]
        f_q_final = f_q_final[f_q_final.index.year.isin(selected_years)].sort_index(ascending=False)
        f_q_final.index = f_q_final.index.to_period('Q').astype(str)
        st.dataframe(f_q_final.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except: st.info("ℹ️ Quarterly data not found.")
        
with t5:
    # --- 1. SELECTION UI ---
    # We pull available months only from the years currently selected in the sidebar
    available_months = sorted(
        prices_df[prices_df.index.year.isin(selected_years)].index.strftime('%Y-%m').unique().tolist(), 
        reverse=True
    )
    
    # Default to the most recent month available
    default_month = [available_months[0]] if available_months else []

    sel_months = st.multiselect(
        "📅 Select Month(s) to Analyze", 
        available_months, 
        default=default_month, 
        key="d_month_selector"
    )

    st.divider()

    try:
        if sel_months:
            # --- 2. LOGIC: CALCULATE RETURNS ON FULL DATASET ---
            # This ensures the first day of the month has a valid return from the previous close
            daily_ret_full = prices_df.pct_change() * 100
            
            # Identify the specific dates belonging to the selected months
            target_indices = prices_df[prices_df.index.strftime('%Y-%m').isin(sel_months)].index
            
            if not target_indices.empty:
                # Filter by BOTH Selected Dates and sidebar-selected Stocks
                day_view = daily_ret_full.loc[target_indices, selected_stocks].copy()

                # --- 3. DYNAMIC SUMMARY (Recalculated for the selected period) ---
                # This ensures the ranking updates when you toggle months
                summary_df = pd.DataFrame({
                    'Total Return (%)': day_view.sum(),
                    'Best Day (%)': day_view.max(),
                    'Worst Day (%)': day_view.min(),
                    'Avg Daily Move (%)': day_view.mean()
                }).sort_values(by='Total Return (%)', ascending=False)

                # Identify winners specifically for the selected month range
                top_2_names = summary_df.head(2).index.tolist()

                # --- 4. PERIOD INSIGHT TILES ---
                overall_winner = summary_df.index[0]
                overall_val = summary_df.iloc[0]['Total Return (%)']
                
                max_val = day_view.max().max()
                best_s = day_view.max().idxmax()
                best_d = day_view[best_s].idxmax().strftime('%d %b %Y')
                
                min_val = day_view.min().min()
                worst_s = day_view.min().idxmin()
                worst_d = day_view[worst_s].idxmin().strftime('%d %b %Y')
                
                t_col1, t_col2, t_col3 = st.columns(3)
                with t_col1:
                    st.metric("🥇 Period Leader", f"{overall_val:.2f}%", f"{overall_winner}")
                with t_col2:
                    st.metric("🚀 Top Daily Move", f"{max_val:.2f}%", f"{best_s} ({best_d})")
                with t_col3:
                    st.metric("📉 Deepest Day Cut", f"{min_val:.2f}%", f"{worst_s} ({worst_d})")
                
                # --- 5. PERFORMANCE SUMMARY TABLE ---
                st.subheader("📊 Performance Ranking (Selected Period)")
                st.dataframe(
                    summary_df.style.background_gradient(cmap='YlGn', subset=['Total Return (%)']).format("{:.2f}%"), 
                    use_container_width=True
                )

                st.write("") 

                # --- 6. TREND CHART ---
                chart_col, ctrl_col = st.columns([4, 1]) 

                with ctrl_col:
                    st.write("🔍 **Chart Filters**")
                    sel_stocks_chart = st.multiselect(
                        "Select Stocks:", 
                        selected_stocks, 
                        default=top_2_names, 
                        key="t5_trend_chart_stocks" 
                    )
                    st.caption("Winners for this specific period are auto-selected.")

                with chart_col:
                    if sel_stocks_chart:
                        st.subheader(f"🕵️ Compounded Growth ({', '.join(sel_months)})")
                        
                        chart_data = day_view[sel_stocks_chart].copy()
                        # Calculate compounded growth starting from 0%
                        cum_trend_pct = ((1 + chart_data / 100).cumprod() - 1) * 100
                        
                        fig_trend = px.line(
                            cum_trend_pct, 
                            template="plotly_white", 
                            labels={"value": "Growth %", "index": "Date"},
                            markers=True,
                            height=450
                        )
                        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
                        fig_trend.update_layout(showlegend=True, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
                        st.plotly_chart(fig_trend, use_container_width=True)

                # --- 7. DAILY HEATMAP ---
                st.subheader("📋 Raw Daily Returns (%)")
                table_display = day_view.copy().sort_index(ascending=False)
                table_display.index = table_display.index.strftime('%Y-%m-%d (%a)')
                
                st.dataframe(
                    table_display.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                    use_container_width=True
                )

                # --- 8. PRICE HISTORY SECTION (The fix is here) ---
                st.subheader("📈 Absolute Price History (Selected Period)")
                
                # Filter raw prices using the same target_indices logic
                period_price_history = prices_df.loc[target_indices, selected_stocks].copy()
                period_price_history.index = period_price_history.index.strftime('%Y-%m-%d')

                st.dataframe(
                    period_price_history.sort_index(ascending=False), 
                    use_container_width=True
                )

                # --- 9. DOWNLOAD BUTTONS ---
                st.divider()
                c_dl1, c_dl2 = st.columns(2)
                with c_dl1:
                    st.download_button(
                        label="📥 Download Daily Returns (CSV)", 
                        data=day_view.to_csv().encode('utf-8'), 
                        file_name=f"returns_{'_'.join(sel_months)}.csv", 
                        mime='text/csv', 
                        use_container_width=True,
                        key="dl_ret_t5"
                    )
                with c_dl2:
                    st.download_button(
                        label="📥 Download Price History (CSV)", 
                        data=period_price_history.to_csv().encode('utf-8'), 
                        file_name=f"prices_{'_'.join(sel_months)}.csv", 
                        mime='text/csv', 
                        use_container_width=True,
                        key="dl_prices_t5"
                    )
# ... (End of your Tab 5 logic, Price History, and Download buttons) ...

    except Exception as e:
        st.error(f"⚠️ Tab 5 Error: {e}")

with t6:
    st.subheader("🔍 Individual Stock Deep-Dive")
    target_stock = st.selectbox("Pick a stock to analyze in detail:", selected_stocks, key="deep_dive_ticker")

    if target_stock:
        s_data = filtered_prices[target_stock].dropna()
        full_series = prices_df[target_stock].dropna()
        ma50 = full_series.rolling(50).mean().loc[s_data.index]
        ma200 = full_series.rolling(200).mean().loc[s_data.index]
        
        # Signal Logic
        if ma50.iloc[-1] > ma200.iloc[-1]: st.success(f"🚀 **Bullish Trend:** Golden Cross")
        else: st.error(f"⚠️ **Bearish Trend:** Death Cross")

        # Metric Cards with Peak Context
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"₹{s_data.iloc[-1]:.2f}")
        c2.metric("Period Return", f"{((s_data.iloc[-1]/s_data.iloc[0])-1)*100:.2f}%")
        c3.metric("Max Price", f"₹{s_data.max():.2f}", f"Peak: {s_data.idxmax().strftime('%d %b %Y')}")
        dd = (s_data / s_data.cummax() - 1) * 100
        c4.metric("Max Drawdown", f"{dd.min():.2f}%", delta_color="inverse")

        # Main Technical Chart with Annotations
        fig_main = px.line(s_data, template="plotly_white", color_discrete_sequence=['#002b5b'], title=f"{target_stock} Technical Trend")
        fig_main.add_scatter(x=ma50.index, y=ma50, name="50 DMA", line=dict(dash='dash', color='orange'))
        fig_main.add_scatter(x=ma200.index, y=ma200, name="200 DMA", line=dict(dash='dot', color='red'))
        fig_main.add_annotation(x=s_data.idxmax(), y=s_data.max(), text="Cycle Peak", showarrow=True, arrowhead=1)
        st.plotly_chart(fig_main, use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l: st.plotly_chart(px.area(dd, title="Peak-to-Trough Drawdown (%)", template="plotly_white", color_discrete_sequence=['#ff4b4b']), use_container_width=True)
        with col_r: st.plotly_chart(px.histogram(s_data.pct_change()*100, nbins=40, title="Daily Return Frequency", template="plotly_white"), use_container_width=True)
