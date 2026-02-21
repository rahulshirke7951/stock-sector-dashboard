import streamlit as st
import pandas as pd
import os
import plotly.express as px

st.set_page_config(page_title="Stock Watchlist", layout="wide")

# --- UI CSS ---
st.markdown("""<style>
    th { background-color: #002b5b !important; color: white !important; text-align: center !important; }
    td { text-align: center !important; }
    .stMetric { border-top: 4px solid #002b5b; background: #f8f9ff; }
</style>""", unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.error("No Excel files found in the 'dashboards' folder. Please run engine.py.")
    st.stop()

with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files)
    file_path = os.path.join(folder, selected_file)
    
    # --- LOAD DATA & METADATA ---
    prices_df = pd.read_excel(file_path, sheet_name="prices", index_col=0)
    prices_df.index = pd.to_datetime(prices_df.index)
    
    # Load Auto-Fetched names from the metadata sheet
    try:
        meta_df = pd.read_excel(file_path, sheet_name="metadata", index_col=0)
        # Convert metadata to a dictionary for renaming
        name_map = meta_df.iloc[:, 0].to_dict()
        prices_df.rename(columns=name_map, inplace=True)
    except Exception as e:
        name_map = {s: s for s in prices_df.columns}

    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    select_all = st.toggle("Select All Stocks", value=True)
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks if select_all else None)
    
    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years = st.multiselect("Years", available_years, default=available_years[:2])

# --- LOGIC & PRESENTATION ---
filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty or not selected_stocks:
    st.warning("⚠️ Select stocks and years.")
    st.stop()

# Performance Stats (CAGR & Returns)
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

st.title(f"📈 {selected_file.replace('.xlsx', '')}")

m1, m2 = st.columns(2)
m1.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.1f}%")
m2.metric("📅 Selection CAGR", "Annualized", f"{df_sum['CAGR %'].mean():.1f}%")

st.divider()

t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance Data", "📅 Monthly", "🏢 Quarterly"])

with t1:
    c1, c2 = st.columns([1, 1.5])
    with c1:
        st.subheader("Return Ranking")
        st.plotly_chart(px.bar(df_sum, x="Return %", y="Ticker", orientation='h', color="Return %", 
                               color_continuous_scale='RdYlGn', template="simple_white"), use_container_width=True)
    with c2:
        st.subheader("Price Trajectory")
        st.plotly_chart(px.line(filtered_prices, template="simple_white"), use_container_width=True)

with t2:
    st.dataframe(df_sum.style.background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
                 .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}), 
                 use_container_width=True, hide_index=True)

with t3:
    st.subheader("Monthly Returns (%)")
    try:
        m_data = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        # Fixed logic: filter columns first, THEN filter index by year
        f_m = m_data[selected_stocks]
        f_m = f_m[f_m.index.year.isin(selected_years)]
        f_m.index = f_m.index.strftime('%Y-%b')
        st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except:
        st.info("ℹ️ Monthly sheet syncing...")

with t4:
    st.subheader("Quarterly Returns (%)")
    try:
        q_data = pd.read_excel(file_path, sheet_name="quarterly_returns", index_col=0)
        q_data.rename(columns=name_map, inplace=True)
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        # FIX: Defined f_q before using it for indexing
        f_q = q_data[selected_stocks]
        f_q = f_q[f_q.index.year.isin(selected_years)]
        f_q.index = f_q.index.to_period('Q').astype(str)
        st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), use_container_width=True)
    except:
        st.info("ℹ️ Quarterly sheet syncing...")
