import streamlit as st
import pandas as pd
import os
import plotly.express as px

# ---------- Page Config ----------
st.set_page_config(page_title="Sector Stock Dashboard", layout="wide", page_icon="📈")

# ---------- Custom CSS (Modern Glassmorphism) ----------
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
    </style>
    """, unsafe_allow_html=True)

# ---------- Load Files ----------
folder = "dashboards"

if not os.path.exists(folder):
    st.error("📂 Folder 'dashboards' not found. Check your file path.")
    st.stop()

# We look for simple names like 'Automobile.xlsx' now
files = sorted([f for f in os.listdir(folder) if f.endswith(".xlsx")])

if not files:
    st.warning("⚠️ No sector files found. Please run your data-fetcher script first.")
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("Settings")
    selected_file = st.selectbox("🎯 Select Sector", files)
    file_path = os.path.join(folder, selected_file)
    st.divider()
    st.caption("Auto-updated daily at 12:00 UTC via GitHub Actions.")

# ---------- Data Loading ----------
try:
    summary = pd.read_excel(file_path, sheet_name="summary")
    cagr = pd.read_excel(file_path, sheet_name="cagr")
    monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
    
    ticker_col = summary.columns[0]
except Exception as e:
    st.error(f"❌ Error reading sheets: {e}")
    st.stop()

# ---------- Header ----------
# Clean up filename for display: 'Automobile.xlsx' -> 'Automobile'
sector_name = selected_file.replace(".xlsx", "").replace("_", " ").title()
st.title(f"📊 {sector_name} Analysis")

# ---------- Metrics ----------
if "Total Return %" in summary.columns:
    # Use loc[idxmax] to get the specific ticker name correctly
    best_row = summary.loc[summary["Total Return %"].idxmax()]
    worst_row = summary.loc[summary["Total Return %"].idxmin()]

    m1, m2, m3 = st.columns(3)
    m1.metric("🏆 Top Performer", best_row[ticker_col], f"{best_row['Total Return %']:.2f}%")
    m2.metric("📉 Worst Performer", worst_row[ticker_col], f"{worst_row['Total Return %']:.2f}%", delta_color="inverse")
    m3.metric("📈 Sector Avg", "Total Return", f"{summary['Total Return %'].mean():.2f}%")

# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["📊 Visuals", "📋 Data", "📅 Monthly Heatmap"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        val_col = cagr.columns[1]
        fig_cagr = px.bar(cagr, x=cagr.columns[0], y=val_col, 
                          title="CAGR by Ticker", color=val_col,
                          color_continuous_scale='RdYlGn')
        st.plotly_chart(fig_cagr, use_container_width=True)
    
    with c2:
        rank_df = summary.sort_values("Total Return %").reset_index()
        fig_rank = px.bar(rank_df, x="Total Return %", y=ticker_col, 
                          orientation='h', title="Total Return Ranking",
                          color="Total Return %", color_continuous_scale='Greens')
        st.plotly_chart(fig_rank, use_container_width=True)

with tab2:
    st.subheader("Performance Summary")
    st.dataframe(summary.style.highlight_max(axis=0, subset=["Total Return %"], color='#d4edda'), 
                 use_container_width=True)

with tab3:
    st.subheader("Monthly Returns Heatmap")
    try:
        styled_monthly = monthly.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%")
        st.dataframe(styled_monthly, use_container_width=True, height=500)
    except:
        st.dataframe(monthly, use_container_width=True)
