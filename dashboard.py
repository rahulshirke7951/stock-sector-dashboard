import streamlit as st
import pandas as pd
import os
import plotly.express as px
from io import BytesIO

st.set_page_config(page_title="Stock Watchlist", layout="wide")

# UI FIX: Navy Blue Headers, White Text, Centered Values
st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e6e9ef; border-top: 4px solid #002b5b; }
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    # Load prices to build dynamic filters
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    # UI REQUEST: Stock Multi-select
    all_stocks = sorted(prices_df.columns.tolist())
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# Filter based on sidebar
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("Please select stocks and years.")
    st.stop()

# CAGR Logic
days_elapsed = (filtered_prices.index[-1] - filtered_prices.index[0]).days
years_n = max(days_elapsed / 365.25, 0.1)

summary = []
for s in selected_stocks:
    col = filtered_prices[s].dropna()
    if len(col) >= 2:
        ret = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr = (((col.iloc[-1] / col.iloc[0]) ** (1/years_n)) - 1) * 100
        summary.append({"Ticker": s, "Return %": ret, "CAGR %": cagr, "Latest": col.iloc[-1]})

df_sum = pd.DataFrame(summary).sort_values("Return %", ascending=False)

# UI FIX: Removed "Terminal" and "Total"
st.title(f"📈 {selected_file.replace('.xlsx', '')}")
st.caption(f"📅 Window: {filtered_prices.index.min().date()} to {filtered_prices.index.max().date()}")

m1, m2 = st.columns(2)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.2f}%")
m2.metric("📅 Selection CAGR", "Avg Annualized", f"{df_sum['CAGR %'].mean():.2f}%")

st.divider()

t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance Data", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", color_continuous_scale='RdYlGn', template="simple_white"), use_container_width=True)
    with c2:
        st.subheader("Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="simple_white"), use_container_width=True)
    
    st.divider()
    st.subheader("🕵️ Rolling Consistency (1Y Window)")
    try:
        roll = pd.read_excel(file_path, sheet_name="rolling_12m", index_col=0)
        roll.index = pd.to_datetime(roll.index)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="simple_white")
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True)
    except: st.info("Syncing rolling data...")

with t2:
    # UI FIX: 2 Decimal precision, centered data
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
                 .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "{:.2f}"}), 
                 use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    m_data.index = pd.to_datetime(m_data.index)
    f_m = m_data[selected_stocks]
    f_m = f_m[f_m.index.year.isin(selected_years)]
    # Convert index back to string for display
    f_m.index = f_m.index.strftime('%Y-%b')
    st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)

with t4:
    st.subheader("Quarterly Returns (%)")
    q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
    q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
    f_q = q_data[selected_stocks]
    f_q = f_q[f_q.index.year.isin(selected_years)]
    # UI FIX: String conversion logic to prevent AttributeErrors
    f_q.index = f_q.index.to_period('Q').astype(str)
    st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
