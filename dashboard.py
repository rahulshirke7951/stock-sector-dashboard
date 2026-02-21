import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

# ---------- Page Config ----------
st.set_page_config(page_title="Pro Sector Analytics", layout="wide", page_icon="📈")

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
    selected_file = st.selectbox("Select Sector", files)
    file_path = os.path.join(folder, selected_file)

    # Load Prices once for the filter
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Select Analysis Years", available_years, default=available_years)

# ---------- Filter & CAGR Logic ----------
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)]

if filtered_prices.empty:
    st.warning("Please select at least one year with data.")
    st.stop()

days_elapsed = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_elapsed = days_elapsed / 365.25

summary_stats = []
for ticker in filtered_prices.columns:
    col_data = filtered_prices[ticker].dropna()
    if len(col_data) >= 2:
        start_val, end_val = col_data.iloc[0], col_data.iloc[-1]
        abs_return = ((end_val / start_val) - 1) * 100
        cagr = (((end_val / start_val) ** (1 / years_elapsed if years_elapsed > 0 else 1)) - 1) * 100
        summary_stats.append({"Ticker": ticker, "Return %": abs_return, "CAGR %": cagr, "Latest": end_val})

df_summary = pd.DataFrame(summary_stats).sort_values("Return %", ascending=False)

# ---------- UI Sections ----------
st.title(f"📊 {selected_file.replace('.xlsx', '')} Terminal")
st.info(f"📅 Period: {filtered_prices.index.min().date()} to {filtered_prices.index.max().date()}")

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", df_summary.iloc[0]['Ticker'], f"{df_summary.iloc[0]['Return %']:.1f}%")
m2.metric("📈 Avg Return", "Sector", f"{df_summary['Return %'].mean():.1f}%")
m3.metric("📅 Avg CAGR", "Annualized", f"{df_summary['CAGR %'].mean():.1f}%")

st.divider()

tab_viz, tab_summary, tab_month, tab_quart = st.tabs([
    "📈 Consistency & Visuals", "📋 Performance Data", "📅 Monthly Heatmap", "🏢 Quarterly Heatmap"
])

with tab_viz:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Total Return Ranking")
        st.plotly_chart(px.bar(df_summary, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="plotly_white"), use_container_width=True)
    with c2:
        st.subheader("Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="plotly_white"), use_container_width=True)

    st.divider()
    st.subheader("🕵️ Consistency Check: 1-Year Rolling Returns")
    st.caption("Stable lines above 0% indicate 'Consistent Compounders'. Window: 252 trading days.")
    
    try:
        # Load FULL rolling data first
        rolling_df = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        rolling_df.index = pd.to_datetime(rolling_df.index)
        
        # Filter ONLY for display - this prevents the "Insufficient Data" error
        display_rolling = rolling_df[rolling_df.index.year.isin(selected_years)]
        
        if not display_rolling.empty:
            fig_roll = px.line(display_rolling, template="plotly_white", labels={"value": "Return %"})
            fig_roll.add_hline(y=0, line_dash="dash", line_color="red", annotation_text="0% Baseline")
            st.plotly_chart(fig_roll, use_container_width=True)
        else:
            st.warning("⚠️ Rolling data requires 1 year of history. If you only select 2024, ensure you have 2023 data in your file.")
    except:
        st.info("Rolling data sheet not found. Run engine.py again.")

with tab_summary:
    st.dataframe(df_summary.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn").format("{:.2f}%", subset=["Return %", "CAGR %"]), use_container_width=True, hide_index=True)
    excel_buffer = BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df_summary.to_excel(writer, index=False)
    st.download_button("📥 Download Report", excel_buffer.getvalue(), f"{selected_file}_report.xlsx")

with tab_month:
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    st.dataframe(m_data[m_data.index.str[:4].astype(int).isin(selected_years)].style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with tab_quart:
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    st.dataframe(q_data[q_data.index.str[:4].astype(int).isin(selected_years)].style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
