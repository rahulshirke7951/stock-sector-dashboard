import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

# ---------- Page Config ----------
st.set_page_config(page_title="Pro Sector Analytics", layout="wide", page_icon="📈")

# Custom Metric Styling
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; box-shadow: 2px 2px 5px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# ---------- Data Loading ----------
folder = "dashboards"
if not os.path.exists(folder):
    st.error(f"📂 Folder '{folder}' not found. Please run engine.py first.")
    st.stop()

files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.error("📂 No Excel files found in the dashboard folder.")
    st.stop()

# ---------- Sidebar Selection ----------
with st.sidebar:
    st.title("🎯 Control Panel")
    selected_file = st.selectbox("Select Sector to Analyze", files)
    file_path = os.path.join(folder, selected_file)

    # Load Prices once to generate the Year Filter
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Filter Analysis Years", available_years, default=available_years)

# ---------- Filtering & CAGR Logic ----------
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)]

if filtered_prices.empty:
    st.warning("No data found for the selected year range.")
    st.stop()

# Dynamic CAGR calculation based on selection
days_elapsed = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_elapsed = days_elapsed / 365.25

summary_stats = []
for ticker in filtered_prices.columns:
    col_data = filtered_prices[ticker].dropna()
    if len(col_data) >= 2:
        start_val = col_data.iloc[0]
        end_val = col_data.iloc[-1]
        
        abs_return = ((end_val / start_val) - 1) * 100
        # CAGR Formula: [(End/Start)^(1/n) - 1] * 100
        cagr = (((end_val / start_val) ** (1 / years_elapsed if years_elapsed > 0 else 1)) - 1) * 100
        
        summary_stats.append({
            "Ticker": ticker, 
            "Start Price": start_val, 
            "Latest Price": end_val, 
            "Return %": abs_return, 
            "CAGR %": cagr
        })

df_summary = pd.DataFrame(summary_stats).sort_values("Return %", ascending=False)

# ---------- UI Sections ----------
sector_display_name = selected_file.replace(".xlsx", "").replace("_", " ")
st.title(f"📊 {sector_display_name} Performance Terminal")
st.info(f"📅 **Selected Period:** {filtered_prices.index.min().strftime('%d %b %Y')} to {filtered_prices.index.max().strftime('%d %b %Y')}")

# Metrics
top_stock = df_summary.iloc[0]
avg_cagr = df_summary["CAGR %"].mean()
avg_ret = df_summary["Return %"].mean()

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", top_stock['Ticker'], f"{top_stock['Return %']:.2f}%")
m2.metric("📈 Avg. Sector Return", "Total", f"{avg_ret:.2f}%")
m3.metric("📅 Avg. Sector CAGR", "Annualized", f"{avg_cagr:.2f}%")

st.divider()

# Tabs
tab_viz, tab_summary, tab_month, tab_quart = st.tabs([
    "📈 Consistency & Visuals", "📋 Performance Data", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap"
])

with tab_viz:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Total Performance Ranking")
        fig_bar = px.bar(df_summary, x="Return %", y="Ticker", orientation='h', 
                         color="Return %", color_continuous_scale='RdYlGn', template="plotly_white")
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with c2:
        st.subheader("Price Trajectory")
        fig_line = px.line(filtered_prices, template="plotly_white")
        st.plotly_chart(fig_line, use_container_width=True)

    st.divider()
    st.subheader("🕵️ Rolling Consistency Check (12-Month Windows)")
    st.caption("A 'Consistent Compounder' stays above the 0% baseline. 'One-Hit Wonders' show huge spikes and crashes.")
    
    try:
        rolling_df = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        rolling_df.index = pd.to_datetime(rolling_df.index)
        filtered_rolling = rolling_df[rolling_df.index.year.isin(selected_years)]
        
        if not filtered_rolling.empty:
            fig_roll = px.line(filtered_rolling, template="plotly_white", labels={"value": "Rolling Return %", "Date": "Timeline"})
            fig_roll.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="0% Baseline")
            st.plotly_chart(fig_roll, use_container_width=True)
        else:
            st.info("Insufficient historical data for rolling calculation in this period.")
    except:
        st.info("Rolling data sheet not found. Run engine.py to generate it.")

with tab_summary:
    st.subheader("Raw Performance Summary")
    st.dataframe(
        df_summary.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
        .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Start Price": "{:.2f}", "Latest Price": "{:.2f}"}),
        use_container_width=True, hide_index=True
    )
    
    # Download Button
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df_summary.to_excel(writer, index=False, sheet_name='Summary')
    st.download_button("📥 Download Summary as Excel", excel_buffer.getvalue(), f"{sector_display_name}_report.xlsx")

with tab_month:
    st.subheader("Monthly Returns (%)")
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    # Filter heatmap by selected years
    filtered_m = m_data[m_data.index.str[:4].astype(int).isin(selected_years)]
    st.dataframe(filtered_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with tab_quart:
    st.subheader("Quarterly Returns (%)")
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    # Filter heatmap by selected years
    filtered_q = q_data[q_data.index.str[:4].astype(int).isin(selected_years)]
    st.dataframe(filtered_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
