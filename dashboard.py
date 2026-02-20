import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ---------- Page Config ----------
st.set_page_config(page_title="Sector Stock Dashboard", layout="wide", page_icon="📈")

# ---------- Custom CSS for Modern UI ----------
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    div.stMetric {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #eee;
    }
    [data-testid="stSidebar"] { background-color: #1e293b; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# ---------- Load Files ----------
folder = "dashboards"

if not os.path.exists(folder):
    st.error("📂 Folder 'dashboards' not found. Ensure your GitHub workflow has run.")
    st.stop()

files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]

if not files:
    st.warning("⚠️ No sector files available yet.")
    st.stop()

# ---------- Sidebar Selection ----------
with st.sidebar:
    st.title("📊 Navigation")
    selected_file = st.selectbox("🎯 Choose Sector", files)
    file_path = os.path.join(folder, selected_file)
    st.divider()
    st.info("💡 Data is refreshed automatically via GitHub Actions.")

# ---------- Data Loading & Processing ----------
try:
    # Load dataframes
    summary = pd.read_excel(file_path, sheet_name="summary")
    cagr = pd.read_excel(file_path, sheet_name="cagr")
    monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)

    # Clean column names (strip spaces just in case)
    summary.columns = summary.columns.str.strip()
    cagr.columns = cagr.columns.str.strip()
    
    # Identify the ticker column (usually the first one)
    ticker_col = summary.columns[0]
    
except Exception as e:
    st.error(f"❌ Error loading Excel sheets: {e}")
    st.stop()

# ---------- Header Section ----------
sector_display = selected_file.split('_')[0].replace(".xlsx", "").title()
st.title(f"📊 {sector_display} Sector Performance")
st.caption(f"Analyzing data from: {selected_file}")

# ---------- Metric Highlights ----------
if "Total Return %" in summary.columns:
    # Calculate key metrics
    best_idx = summary["Total Return %"].idxmax()
    best_stock = summary.loc[best_idx, ticker_col]
    best_val = summary.loc[best_idx, "Total Return %"]

    worst_idx = summary["Total Return %"].idxmin()
    worst_stock = summary.loc[worst_idx, ticker_col]
    worst_val = summary.loc[worst_idx, "Total Return %"]

    avg_ret = summary["Total Return %"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("🏆 Top Performer", f"{best_stock}", f"{best_val:.2f}%")
    m2.metric("📉 Worst Performer", f"{worst_stock}", f"{worst_val:.2f}%", delta_color="inverse")
    m3.metric("📈 Sector Average", "Total Return", f"{avg_ret:.2f}%")

st.divider()

# ---------- Tabs Layout ----------
tab_visuals, tab_summary, tab_monthly = st.tabs(["📊 Performance Visuals", "📋 Summary Data", "📅 Monthly Heatmap"])

with tab_visuals:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("CAGR (%)")
        # Ensure we have a value column to plot
        val_col = cagr.columns[1]
        fig_cagr = px.bar(cagr, x=cagr.columns[0], y=val_col, 
                          color=val_col, color_continuous_scale='RdYlGn',
                          labels={val_col: 'CAGR %', cagr.columns[0]: 'Ticker'})
        fig_cagr.update_layout(showlegend=False)
        st.plotly_chart(fig_cagr, use_container_width=True)

    with col_right:
        st.subheader("Total Return Ranking")
        ranking_df = summary.sort_values("Total Return %", ascending=True)
        fig_rank = px.bar(ranking_df, x="Total Return %", y=ticker_col, 
                          orientation='h', color="Total Return %",
                          color_continuous_scale='Greens')
        st.plotly_chart(fig_rank, use_container_width=True)

with tab_summary:
    st.subheader("Sector Summary Table")
    # Display summary with a green highlight on the max values
    st.dataframe(summary.style.highlight_max(axis=0, subset=["Total Return %"], color='#d4edda'), 
                 use_container_width=True)
    
    st.subheader("CAGR Raw Data")
    st.dataframe(cagr, use_container_width=True)

with tab_monthly:
    st.subheader("Monthly Returns Heatmap")
    st.markdown("Returns are color-coded: **Red** (Negative) to **Green** (Positive).")
    
    # Advanced Heatmap Styling (Requires Matplotlib)
    try:
        styled_monthly = monthly.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%")
        st.dataframe(styled_monthly, use_container_width=True, height=500)
    except Exception as e:
        st.warning("Heatmap styling failed. Displaying raw numbers.")
        st.dataframe(monthly, use_container_width=True)

# ---------- Footer ----------
st.divider()
st.caption(f"Dashboard generated for {sector_display} Sector. Powered by Streamlit & Plotly.")
