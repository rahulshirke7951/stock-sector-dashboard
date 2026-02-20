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
    [data-testid="stSidebar"] { background-color: #1e293b; color: white; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# ---------- Load Files ----------
folder = "dashboards"

if not os.path.exists(folder):
    st.error("📂 No 'dashboards' folder found. Please run the GitHub workflow first.")
    st.stop()

files = [f for f in os.listdir(folder) if f.endswith(".xlsx")]

if not files:
    st.warning("⚠️ No sector files generated yet.")
    st.stop()

# ---------- Sidebar Selection ----------
with st.sidebar:
    st.title("Settings")
    selected_file = st.selectbox("🎯 Select Sector", files)
    file_path = os.path.join(folder, selected_file)
    st.divider()
    st.caption("Data updated automatically via GitHub Actions.")

# ---------- Data Loading ----------
try:
    summary = pd.read_excel(file_path, sheet_name="summary", index_col=0)
    cagr = pd.read_excel(file_path, sheet_name="cagr", index_col=0)
    monthly = pd.read_excel(file_path, sheet_name="monthly_returns", index_col=0)
except Exception as e:
    st.error(f"❌ Error reading sheets: {e}")
    st.stop()

# ---------- Header Section ----------
sector_name = selected_file.replace(".xlsx", "").replace("_", " ").title()
st.title(f"📊 {sector_name} Analysis")
st.markdown(f"Examine the performance and growth metrics for the **{sector_name}** universe.")

# ---------- Top Highlights (Metrics) ----------
if "Total Return %" in summary.columns:
    best_stock = summary["Total Return %"].idxmax()
    best_value = summary["Total Return %"].max()
    worst_stock = summary["Total Return %"].idxmin()
    worst_value = summary["Total Return %"].min()
    avg_return = summary["Total Return %"].mean()

    m1, m2, m3 = st.columns(3)
    m1.metric("🏆 Top Performer", best_stock, f"{best_value:.2f}%")
    m2.metric("📉 Worst Performer", worst_stock, f"{worst_value:.2f}%", delta_color="inverse")
    m3.metric("📈 Sector Average", "Total Return", f"{avg_return:.2f}%")

st.divider()

# ---------- Main Dashboard Tabs ----------
tab_visuals, tab_data, tab_monthly = st.tabs(["📈 Performance Visuals", "📋 Detailed Summary", "📅 Monthly Heatmap"])

with tab_visuals:
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("CAGR by Ticker")
        # Ensure cagr has a value column to plot
        fig_cagr = px.bar(cagr, x=cagr.index, y=cagr.columns[0], 
                          labels={'index': 'Ticker', 'value': 'CAGR %'},
                          color=cagr.columns[0], color_continuous_scale='RdYlGn')
        fig_cagr.update_layout(showlegend=False, height=450)
        st.plotly_chart(fig_cagr, use_container_width=True)

    with col_right:
        st.subheader("Total Return Ranking")
        ranking = summary.sort_values("Total Return %", ascending=True)
        fig_rank = px.bar(ranking, x="Total Return %", y=ranking.index, 
                          orientation='h', color="Total Return %",
                          color_continuous_scale='Greens')
        fig_rank.update_layout(height=450)
        st.plotly_chart(fig_rank, use_container_width=True)

with tab_data:
    st.subheader("Full Sector Summary")
    st.dataframe(summary.style.highlight_max(axis=0, color='#d4edda'), use_container_width=True)
    
    st.subheader("CAGR Raw Data")
    st.dataframe(cagr, use_container_width=True)

with tab_monthly:
    st.subheader("Monthly Returns Heatmap")
    st.write("Percentage returns color-coded by performance intensity.")
    
    # Advanced styling: Gradient heatmap
    styled_monthly = monthly.style.background_gradient(cmap='RdYlGn', axis=None).format("{:.2f}%")
    st.dataframe(styled_monthly, use_container_width=True, height=500)

# ---------- Footer ----------
st.divider()
st.caption(f"Showing data for {selected_file}. Use the sidebar to switch sectors.")
