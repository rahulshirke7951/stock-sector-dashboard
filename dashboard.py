import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Pro Sector Analytics", layout="wide", page_icon="📈")

# UI Styling
st.markdown("""<style>.stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; }</style>""", unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.error("📂 No data found. Ensure engine.py runs in GitHub Actions.")
    st.stop()

with st.sidebar:
    st.title("🎯 Control Panel")
    selected_file = st.selectbox("Select Sector", files)
    file_path = os.path.join(folder, selected_file)

    # Load Prices to drive the filter
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Select Years", available_years, default=available_years)

# --- Logic: Filter & CAGR ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)]
if filtered_prices.empty:
    st.warning("No data for selected years.")
    st.stop()

days_elapsed = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_elapsed = days_elapsed / 365.25

summary_list = []
for ticker in filtered_prices.columns:
    col = filtered_prices[ticker].dropna()
    if len(col) >= 2:
        ret = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr = (((col.iloc[-1] / col.iloc[0]) ** (1 / years_elapsed if years_elapsed > 0 else 1)) - 1) * 100
        summary_list.append({"Ticker": ticker, "Return %": ret, "CAGR %": cagr, "Latest": col.iloc[-1]})

df_summary = pd.DataFrame(summary_list).sort_values("Return %", ascending=False)

# --- Display ---
st.title(f"📊 {selected_file.replace('.xlsx', '')} Analysis")
st.info(f"📅 Window: {filtered_prices.index.min().date()} to {filtered_prices.index.max().date()}")

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer", df_summary.iloc[0]['Ticker'], f"{df_summary.iloc[0]['Return %']:.1f}%")
m2.metric("📈 Avg Return", "Sector", f"{df_summary['Return %'].mean():.1f}%")
m3.metric("📅 Avg CAGR", "Annualized", f"{df_summary['CAGR %'].mean():.1f}%")

st.divider()

t1, t2, t3, t4 = st.tabs(["📈 Visuals", "📋 Summary", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.plotly_chart(px.bar(df_summary, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="plotly_white"), use_container_width=True)
    with c2:
        st.plotly_chart(px.line(filtered_prices, template="plotly_white", title="Price Trajectory"), use_container_width=True)

with t2:
    st.dataframe(df_summary.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn").format("{:.2f}%", subset=["Return %", "CAGR %"]), use_container_width=True, hide_index=True)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_summary.to_excel(writer, index=False)
    st.download_button("📥 Download Filtered Excel", output.getvalue(), f"{selected_file}_report.xlsx")

with t3:
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    st.dataframe(m_data[m_data.index.str[:4].astype(int).isin(selected_years)].style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"), use_container_width=True)

with t4:
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    st.dataframe(q_data[q_data.index.str[:4].astype(int).isin(selected_years)].style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"), use_container_width=True)
