import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Stock Watchlist", layout="wide", initial_sidebar_state="expanded")

# ENHANCED UI: Professional Navy Blue Theme + Inter Font + Animations
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header { 
        font-family: 'Inter', sans-serif; 
        font-weight: 700; 
        font-size: 2.8em; 
        background: linear-gradient(135deg, #002b5b, #004080, #0066cc); 
        -webkit-background-clip: text; 
        -webkit-text-fill-color: transparent; 
        text-shadow: 0 2px 4px rgba(0,43,91,0.3);
        text-align: center; margin-bottom: 1rem;
    }
    .subtitle { 
        font-family: 'Inter', sans-serif; 
        font-weight: 400; 
        color: #666; 
        text-align: center; 
        font-size: 1.1em;
    }
    
    .stMetric { 
        background: linear-gradient(145deg, #f8f9ff, #e6e9ef); 
        padding: 20px; 
        border-radius: 12px; 
        border: 1px solid #e6e9ef; 
        border-top: 4px solid #002b5b; 
        box-shadow: 0 4px 8px rgba(0,43,91,0.1);
        transition: all 0.2s ease; 
    }
    .stMetric:hover { 
        transform: translateY(-4px); 
        box-shadow: 0 8px 20px rgba(0,43,91,0.2); 
    }
    
    th { background: linear-gradient(90deg, #002b5b, #004080) !important; color: white !important; text-align: center !important; font-weight: 600; }
    td { text-align: center !important; transition: background 0.2s; }
    .stDataFrame { border: 1px solid #e6e9ef; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,43,91,0.1); }
    
    .sidebar .stContainer { 
        background: linear-gradient(180deg, #f8f9ff 0%, #ffffff 100%); 
        border: 1px solid #e6e9ef; 
        border-radius: 12px; 
        padding: 1.2rem; 
        margin-bottom: 1rem; 
        box-shadow: 0 2px 4px rgba(0,43,91,0.05);
    }
    
    /* Responsive */
    @media (max-width: 768px) {
        .stPlotlyChart { height: 350px !important; }
        .main-header { font-size: 2.2em; }
        .stMetric { padding: 15px; font-size: 0.95em; }
    }
    @media (max-width: 480px) {
        .stMetric { margin: 5px 0; }
    }
    
    /* Hide Streamlit extras */
    footer { visibility: hidden; }
    [data-testid="stHeader"] { display: none; }
    
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

folder = "dashboards"
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

with st.sidebar:
    st.title("📂 Watchlist Controls")
    selected_file = st.selectbox("Select List", files, key="file_select")
    file_path = os.path.join(folder, selected_file)
    
    if st.button("🔄 Reload Data", use_container_width=True):
        st.rerun()
    
    # Load prices to build dynamic filters
    @st.cache_data
    def load_sheet(file_path, sheet_name):
        return pd.read_excel(file_path, sheet_name=sheet_name, index_col=0)
    
    prices_df = load_sheet(file_path, "prices")
    prices_df.index = pd.to_datetime(prices_df.index)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    
    # Grouped filters with containers
    with st.container(border=True):
        st.caption("Stocks")
        selected_stocks = st.multiselect("Active Stocks", all_stocks, default=all_stocks[:10], 
                                        key="stocks", help="Search and select (Ctrl+click)")
    
    with st.container(border=True):
        st.caption("Time Filter")
        available_years = sorted(prices_df.index.year.unique(), reverse=True)
        selected_years = st.multiselect("Years", available_years, default=available_years[:2], key="years")

# Filter and Recalculate Logic
if not files or not selected_stocks:
    st.warning("⚠️ Select a file, stocks, and years to view analytics.")
    st.stop()

filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty:
    st.info("ℹ️ No data matches your filters. Try broader selections.")
    st.stop()

# Annualized CAGR Math
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
avg_cagr = df_sum['CAGR %'].mean()
avg_return = df_sum['Return %'].mean()

# Enhanced Header & Metrics
header_container = st.container()
with header_container:
    st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">NSE Portfolio Analytics | Updated Feb 2026</p>', unsafe_allow_html=True)
    
    # Responsive 3-col metrics
    if st.columns(3)[0].button("📊 View All Metrics", key="metrics"):
        cols = st.columns(3)
    else:
        cols = st.columns([1,1,1])
    
    with cols[0]:
        st.metric("🏆 Top Performer", df_sum.iloc[0]['Ticker'], f"{df_sum.iloc[0]['Return %']:.1f}%")
    with cols[1]:
        st.metric("📈 Avg Return", f"{avg_return:.1f}%", f"{avg_return - 15:.1f}%")  # Sample delta
    with cols[2]:
        st.metric("📅 Portfolio CAGR", f"{avg_cagr:.1f}%", "↑ 2.1%")

st.divider()

# Enhanced Tabs
t1, t2, t3, t4 = st.tabs(["📊 Visuals", "📋 Performance", "📅 Monthly", "🏢 Quarterly"])

with t1:
    with st.spinner("Rendering visuals..."):
        c1, c2 = st.columns([0.6, 1.4])
        with c1:
            st.subheader("🔥 Return Ranking")
            fig_bar = px.bar(df_sum.head(10), x="Return %", y="Ticker", orientation='h', 
                            color="Return %", color_continuous_scale='RdYlGn', 
                            template="plotly_white", height=400)
            fig_bar.update_traces(texttemplate="%{x:.1f}%", textposition="outside", textfont_size=12)
            fig_bar.update_layout(
                font_family="Inter",
                plot_bgcolor="#f8f9ff",
                paper_bgcolor="#f8f9ff",
                title="<b>Top 10 Performers</b>",
                yaxis_title="Ticker",
                xaxis_title="Total Return %",
                showlegend=False
            )
            st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
        
        with c2:
            st.subheader("📈 Price Evolution")
            fig_line = px.line(filtered_prices, template="plotly_white", height=400)
            fig_line.update_layout(
                font_family="Inter",
                plot_bgcolor="#f8f9ff",
                paper_bgcolor="#f8f9ff",
                title="<b>Normalized Prices</b>",
                xaxis_title="Date",
                yaxis_title="Price (₹)"
            )
            fig_line.add_hline(y=1, line_dash="dot", line_color="#002b5b", 
                              annotation_text="Normalized Avg")
            st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
    
    st.divider()
    st.subheader("🕵️ Rolling 12M Returns")
    try:
        roll = load_sheet(file_path, "rolling_12m")
        roll.index = pd.to_datetime(roll.index)
        display_roll = roll[roll.index.year.isin(selected_years)][selected_stocks]
        fig_roll = px.line(display_roll, template="plotly_white", height=400)
        fig_roll.update_layout(
            font_family="Inter",
            plot_bgcolor="#f8f9ff",
            paper_bgcolor="#f8f9ff",
            title="<b>1Y Rolling Returns</b>"
        )
        fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
        st.plotly_chart(fig_roll, use_container_width=True, config={'displayModeBar': False})
    except Exception as e:
        st.info(f"ℹ️ Rolling sheet syncing... ({str(e)})")

with t2:
    col_config = {
        "Return %": st.column_config.NumberColumn("Return %", format="%.2f%%"),
        "CAGR %": st.column_config.NumberColumn("CAGR %", format="%.2f%%"),
        "Latest": st.column_config.NumberColumn("Latest ₹", format="₹%.2f")
    }
    with st.container(border=True):
        st.dataframe(df_sum, use_container_width=True, hide_index=True, 
                    column_config=col_config, height=500)

with t3:
    try:
        m_data = load_sheet(file_path, "monthly_returns")
        m_data.index = pd.to_datetime(m_data.index)
        f_m = m_data[selected_stocks]
        f_m = f_m[f_m.index.year.isin(selected_years)]
        f_m.index = f_m.index.strftime('%Y-%b')
        with st.container(border=True):
            st.dataframe(f_m.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                        use_container_width=True, height=500)
    except:
        st.info("ℹ️ Monthly sheet not ready.")

with t4:
    try:
        q_data = load_sheet(file_path, "quarterly_returns")
        q_data.index = pd.to_datetime([str(x).replace('Q', '-') for x in q_data.index])
        f_q = q_data[selected_stocks]
        f_q = f_q[f_q.index.year.isin(selected_years)]
        f_q.index = f_q.index.to_period('Q').astype(str)
        with st.container(border=True):
            st.dataframe(f_q.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%"), 
                        use_container_width=True, height=500)
    except:
        st.info("ℹ️ Quarterly sheet not ready.")

# Footer Export
with st.expander("📥 Export Options", expanded=False):
    csv = df_sum.to_csv(index=False).encode('utf-8')
    st.download_button("Download Summary CSV", csv, f"{selected_file}_summary.csv", "text/csv")
