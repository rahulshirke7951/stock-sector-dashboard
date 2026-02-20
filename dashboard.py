import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Pro Sector Analytics", layout="wide", page_icon="📈")

# Style
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.error("📂 No data found. Please ensure the 'engine.py' has run successfully.")
    st.stop()

with st.sidebar:
    st.title("🎯 Control Panel")
    selected_file = st.selectbox("Select Sector", files)
    file_path = os.path.join(folder, selected_file)

    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Select Analysis Years", available_years, default=available_years)

# --- DYNAMIC FILTERING & CAGR MATH ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)]

if filtered_prices.empty:
    st.warning("No data for selected years.")
    st.stop()

# Calculate days for CAGR
days_elapsed = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_elapsed = days_elapsed / 365.25

summary_list = []
for ticker in filtered_prices.columns:
    col_data = filtered_prices[ticker].dropna()
    if len(col_data) >= 2:
        start_p = col_data.iloc[0]
        end_p = col_data.iloc[-1]
        ret = ((end_p / start_p) - 1) * 100
        # Calculate CAGR based on the FILTERED period
        cagr = (((end_p / start_p) ** (1 / years_elapsed if years_elapsed > 0 else 1)) - 1) * 100
        summary_list.append({"Ticker": ticker, "Start": start_p, "Latest": end_p, "Return %": ret, "CAGR %": cagr})

dynamic_summary = pd.DataFrame(summary_list).sort_values("Return %", ascending=False)

# Load Heatmaps
monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
quarterly = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)

filtered_m = monthly[monthly.index.str[:4].astype(int).isin(selected_years)]
filtered_q = quarterly[quarterly.index.str[:4].astype(int).isin(selected_years)]

# --- HEADER ---
sector_name = selected_file.replace(".xlsx", "").replace("_", " ").title()
st.title(f"📊 {sector_name} Sector Analysis")
st.info(f"📅 **Analysis Window:** {filtered_prices.index.min().strftime('%d %b %Y')} to {filtered_prices.index.max().strftime('%d %b %Y')}")

# --- METRICS ---
top_row = dynamic_summary.iloc[0]
avg_ret = dynamic_summary["Return %"].mean()
avg_cagr = dynamic_summary["CAGR %"].mean()

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", top_row['Ticker'], f"{top_row['Return %']:.2f}%")
m2.metric("📈 Period Avg Return", "Total", f"{avg_ret:.2f}%")
m3.metric("📅 Period Avg CAGR", "Annualized", f"{avg_cagr:.2f}%")

st.divider()

# --- TABS ---
tab_viz, tab_data, tab_month, tab_quart = st.tabs(["📈 Visuals", "📋 Summary", "📅 Monthly", "🏢 Quarterly"])

with tab_viz:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        fig_bar = px.bar(dynamic_summary, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="plotly_white")
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
    with c2:
        fig_line = px.line(filtered_prices, template="plotly_white")
        st.plotly_chart(fig_line, use_container_width=True)

with tab_data:
    st.dataframe(dynamic_summary.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn").format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Start": "{:.2f}", "Latest": "{:.2f}"}), use_container_width=True, hide_index=True)
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        dynamic_summary.to_excel(writer, index=False, sheet_name='Summary')
    st.download_button("📥 Download Excel Report", output.getvalue(), f"{sector_name}_Analysis.xlsx")

with tab_month:
    st.dataframe(filtered_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with tab_quart:
    st.dataframe(filtered_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
