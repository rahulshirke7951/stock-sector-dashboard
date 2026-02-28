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
    
    # Logic: if toggle is off, default is empty []; if on, default is all stocks
    current_default = all_stocks if select_all else []
    
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=current_default)

    
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

# --- MAIN METRIC TILES (REFINED DESIGN) ---
m1, m2, m3 = st.columns(3)

# 1. Top Performer: Big % and Small Stock Name
top_val = df_sum.iloc[0]['Return %']
top_name = df_sum.iloc[0]['Ticker']
m1.metric("🏆 Top Performer", f"{top_val:.1f}%", f"Stock: {top_name}")

# 2. Avg Return: Big % 
avg_ret = df_sum['Return %'].mean()
m2.metric("📈 Selection Avg Return", f"{avg_ret:.1f}%", "Overall Portfolio")

# 3. CAGR: Big % 
avg_cagr = df_sum['CAGR %'].mean()
m3.metric("📅 Annualized CAGR", f"{avg_cagr:.1f}%", f"Over {years_val:.1f} Years")

st.divider()

# --- TABS ---
t1, t2, t3, t4, t5, t6 = st.tabs(["📊 Visuals", "📋 Performance Stats", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap","📆 Daily Heatmap","🔍 Individual Stock Deep-Dive"])

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
    # 1. Selection UI
    available_months = sorted(
        prices_df[prices_df.index.year.isin(selected_years)].index.strftime('%Y-%m').unique().tolist(), 
        reverse=True
    )
    default_month = [available_months[0]] if available_months else []

    sel_months = st.multiselect("📅 Select Month(s) to Analyze", available_months, default=default_month, key="d_month")

    st.divider()

    try:
        # --- LOGIC: Calculate returns on FULL dataset first for bridge accuracy ---
        daily_ret_full = prices_df.pct_change() * 100
        
        # Identify the specific dates for the selected months
        target_indices = prices_df[prices_df.index.strftime('%Y-%m').isin(sel_months)].index
        
        if not target_indices.empty:
            # --- CRITICAL FIX: Filter by BOTH Selected Dates AND Selected Stocks ---
            day_view = daily_ret_full.loc[target_indices, selected_stocks].copy()

            # --- STEP 1: DYNAMIC SUMMARY (Recalculated for the selected period) ---
            # This ensures the ranking changes when you change months
            summary_df = pd.DataFrame({
                'Total Return (%)': day_view.sum(),
                'Best Day (%)': day_view.max(),
                'Worst Day (%)': day_view.min(),
                'Avg Daily Move (%)': day_view.mean()
            }).sort_values(by='Total Return (%)', ascending=False) # Re-ranks every time UI changes

            # --- STEP 2: DYNAMIC TOP 2 WINNERS ---
            # These are now the winners OF THE SELECTED MONTH(S) only
            top_2_names = summary_df.head(2).index.tolist()

            # --- STEP 3: INSIGHT TILES (Update based on new summary) ---
            overall_winner = summary_df.index[0]
            overall_val = summary_df.iloc[0]['Total Return (%)']
            
            max_val, min_val = day_view.max().max(), day_view.min().min()
            best_s = day_view.max().idxmax()
            best_d = day_view[best_s].idxmax().strftime('%d %b %Y')
            
            worst_s = day_view.min().idxmin()
            worst_d = day_view[worst_s].idxmin().strftime('%d %b %Y')
            
            t_col1, t_col2, t_col3 = st.columns(3)
            with t_col1:
                st.metric("🥇 Period Leader", f"{overall_val:.2f}%", f"{overall_winner}")
            with t_col2:
                st.metric("🚀 Top Daily Move", f"{max_val:.2f}%", f"{best_s} ({best_d})")
            with t_col3:
                st.metric("📉 Deepest Day Cut", f"{min_val:.2f}%", f"{worst_s} ({worst_d})")
            
            # --- STEP 4: PERFORMANCE SUMMARY TABLE (Re-ranked List) ---
            st.subheader("📊 Performance Deep-Dive")
            st.dataframe(
                summary_df.style.background_gradient(cmap='YlGn', subset=['Total Return (%)']).format("{:.2f}%"), 
                use_container_width=True
            )

            st.write("") 

            # --- STEP 5: TREND CHART ---
            chart_col, ctrl_col = st.columns([4, 1]) 

            with ctrl_col:
                st.write("🔍 **Chart Filters**")
                sel_stocks_chart = st.multiselect(
                    "Select Stocks:", 
                    selected_stocks, 
                    default=top_2_names, 
                    key=f"chart_select_{sel_months}" # Key ensures refresh on month change
                )
                st.caption("Winners for selected period are auto-selected.")

            with chart_col:
                if sel_stocks_chart:
                    st.subheader(f"🕵️ Performance Trend ({', '.join(sel_months)})")
                    
                    chart_data = day_view[sel_stocks_chart].copy()
                    # Calculate compounded growth starting from 0% at the start of the selection
                    cum_trend_pct = ((1 + chart_data / 100).cumprod() - 1) * 100
                    
                    fig_trend = px.line(
                        cum_trend_pct, 
                        template="plotly_white", 
                        labels={"value": "Total Growth %", "index": "Date"},
                        markers=True,
                        height=450
                    )
                    fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
                    fig_trend.update_layout(showlegend=False, hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
                    st.plotly_chart(fig_trend, use_container_width=True)

            # --- STEP 6: DAILY HEATMAP ---
            st.subheader("📋 Daily Returns Detail (%)")
            table_display = day_view.copy().sort_index(ascending=False)
            table_display.index = table_display.index.strftime('%Y-%m-%d (%a)')
            
            st.dataframe(
                table_display.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                use_container_width=True
            )

            # --- STEP 7: DOWNLOAD ---
            st.divider()
            csv_prices = filtered_prices.to_csv().encode('utf-8')
            st.download_button(label="📥 Download Filtered Price History (CSV)", data=csv_prices, file_name="prices.csv", mime='text/csv', use_container_width=True)
            
        else:
            st.info("Please select a valid month.")

    except Exception as e:
        st.error(f"An error occurred: {e}")

with t6:
    st.subheader("🔍 Individual Stock Deep-Dive")
    
    # 1. Selection
    target_stock = st.selectbox("Pick a stock to analyze in detail:", selected_stocks, key="deep_dive_ticker")

if target_stock:
        # --- UPDATED DATA PREP ---
        # 1. Get the stock data for the filtered period (for display)
        s_data = filtered_prices[target_stock].dropna()
        
        # 2. Calculate MAs on the FULL master dataframe (so lines show up immediately)
        full_series = prices_df[target_stock].dropna()
        full_ma50 = full_series.rolling(window=50).mean()
        full_ma200 = full_series.rolling(window=200).mean()
        
        # 3. Align the MAs and calculate Watchlist Avg for comparison
        ma50 = full_ma50.loc[s_data.index]
        ma200 = full_ma200.loc[s_data.index]
        
        # 4. Calculate stats on the filtered slice
        total_ret = ((s_data.iloc[-1] / s_data.iloc[0]) - 1) * 100
        max_price = s_data.max()
        max_date = s_data.idxmax().strftime('%d %b %Y')
        
        # 5. Calculate Drawdown
        rolling_max = s_data.cummax()
        drawdown = (s_data / rolling_max - 1) * 100

        # --- SIGNAL LOGIC (Golden/Death Cross) ---
        last_ma50 = ma50.iloc[-1]
        last_ma200 = ma200.iloc[-1]
        
        if last_ma50 > last_ma200:
            st.success(f"🚀 **Bullish Trend:** {target_stock} is in a **Golden Cross** phase (50 DMA > 200 DMA).")
        elif last_ma50 < last_ma200:
            st.error(f"⚠️ **Bearish Trend:** {target_stock} is in a **Death Cross** phase (50 DMA < 200 DMA).")
        else:
            st.info("🔄 **Neutral Trend:** Moving averages are currently converging.")

        # --- TOP METRIC CARDS ---
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"₹{s_data.iloc[-1]:.2f}")
        c2.metric("Period Return", f"{total_ret:.2f}%")
        c3.metric("Max Price", f"₹{max_price:.2f}", f"Peak: {max_date}", delta_color="normal")
        c4.metric("Max Drawdown", f"{drawdown.min():.2f}%", delta_color="inverse")

        st.divider()

        # --- MAIN CHART: PRICE + 50 DMA + 200 DMA ---
        
        st.write(f"### 📈 {target_stock} Technical Trend (Price & MAs)")
        
        fig_main = px.line(s_data, template="plotly_white", color_discrete_sequence=['#002b5b'])
        fig_main.add_scatter(x=ma50.index, y=ma50, name="50 DMA", line=dict(dash='dash', color='orange', width=1.5))
        fig_main.add_scatter(x=ma200.index, y=ma200, name="200 DMA", line=dict(dash='dot', color='red', width=1.5))
      
    
        # Annotate Peak
        fig_main.add_annotation(x=s_data.idxmax(), y=max_price, text="Cycle Peak", 
                                showarrow=True, arrowhead=1, bgcolor="white", opacity=0.8)
        
        fig_main.update_layout(hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig_main, use_container_width=True)

        # --- BOTTOM ROW: DRAWDOWN & DISTRIBUTION ---
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.write("### 📉 Peak-to-Trough Drawdown (%)")
            fig_dd = px.area(drawdown, template="plotly_white", color_discrete_sequence=['#ff4b4b'])
            st.plotly_chart(fig_dd, use_container_width=True)

        with col_right:
            st.write("### 📊 Daily Return Frequency")
            daily_pct = s_data.pct_change().dropna() * 100
            fig_hist = px.histogram(daily_pct, nbins=40, template="plotly_white", color_discrete_sequence=['#0066cc'])
            fig_hist.add_vline(x=0, line_color="black", line_dash="dash")
            st.plotly_chart(fig_hist, use_container_width=True)
