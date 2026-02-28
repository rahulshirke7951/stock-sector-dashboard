import streamlit as st
import pandas as pd
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
FOLDER = "dashboards"
SHEET_PRICES         = "prices"
SHEET_METADATA       = "metadata"
SHEET_ROLLING_12M    = "rolling_12m"
SHEET_MONTHLY        = "monthly_returns"
SHEET_QUARTERLY      = "quarterly_returns"

BRAND_DARK  = "#002b5b"
BRAND_MID   = "#004080"
BRAND_LIGHT = "#0066cc"

# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Stock Watchlist Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600;700&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
    font-family: 'DM Sans', sans-serif;
}}

.main-header {{
    font-family: 'DM Sans', sans-serif;
    font-weight: 700;
    font-size: 2.6em;
    background: linear-gradient(135deg, {BRAND_DARK}, {BRAND_MID}, {BRAND_LIGHT});
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-align: center;
    margin-bottom: 0.4rem;
    letter-spacing: -0.5px;
}}

.info-chip {{
    font-family: 'DM Mono', monospace;
    font-weight: 500;
    color: {BRAND_DARK};
    text-align: center;
    font-size: 0.78em;
    background: #f0f4fa;
    padding: 6px 14px;
    border-radius: 20px;
    display: block;
    margin: 0 auto;
    width: fit-content;
    border: 1px solid #d8e3f0;
    letter-spacing: 0.02em;
}}

.stMetric {{
    background: white;
    padding: 20px;
    border-radius: 14px;
    border: 1px solid #e6ecf5;
    border-top: 4px solid {BRAND_DARK};
    box-shadow: 0 2px 8px rgba(0,43,91,0.07);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.stMetric:hover {{
    transform: translateY(-3px);
    box-shadow: 0 8px 18px rgba(0,43,91,0.13);
}}

th {{
    background-color: {BRAND_DARK} !important;
    color: white !important;
    text-align: center !important;
    font-family: 'DM Sans', sans-serif !important;
}}
td {{ text-align: center !important; }}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CACHED DATA LOADERS
# ─────────────────────────────────────────────
@st.cache_data(show_spinner="Loading price data…")
def load_prices(file_path: str) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=SHEET_PRICES, index_col=0)
    df.index = pd.to_datetime(df.index)
    return df

@st.cache_data(show_spinner=False)
def load_name_map(file_path: str) -> dict:
    try:
        meta = pd.read_excel(file_path, sheet_name=SHEET_METADATA, index_col=0)
        return meta.iloc[:, 0].to_dict()
    except Exception:
        return {}

@st.cache_data(show_spinner=False)
def load_sheet(file_path: str, sheet: str) -> pd.DataFrame | None:
    try:
        return pd.read_excel(file_path, sheet_name=sheet, index_col=0)
    except Exception:
        return None


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def calc_summary(filtered_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-stock return / CAGR using each stock's own valid date range.
    Fixes the shared-years_val bug.
    """
    rows = []
    for ticker in filtered_df.columns:
        col = filtered_df[ticker].dropna()
        if len(col) < 2:
            continue
        days  = (col.index[-1] - col.index[0]).days
        yrs   = max(days / 365.25, 0.1)
        ret   = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr  = (((col.iloc[-1] / col.iloc[0]) ** (1 / yrs)) - 1) * 100
        rows.append({
            "Ticker":    ticker,
            "Return %":  ret,
            "CAGR %":    cagr,
            "Latest":    col.iloc[-1],
            "_years":    yrs,
        })
    return pd.DataFrame(rows).sort_values("Return %", ascending=False)


# ─────────────────────────────────────────────
# FOLDER GUARD
# ─────────────────────────────────────────────
if not os.path.exists(FOLDER):
    st.error(f"🚨 Folder '{FOLDER}' not found. Please run your engine script first.")
    st.stop()

files = sorted([f for f in os.listdir(FOLDER) if f.endswith(".xlsx")])
if not files:
    st.error("🚨 No .xlsx files found in the dashboards folder.")
    st.stop()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("📂 Watchlist Controls")

    selected_file = st.selectbox("Select Watchlist", files, key="main_file_select")
    file_path = os.path.join(FOLDER, selected_file)

    if st.button("🔄 Reload & Sync Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    name_map   = load_name_map(file_path)
    prices_df  = load_prices(file_path)
    prices_df.rename(columns=name_map, inplace=True)
    all_stocks = sorted(prices_df.columns.tolist())

    st.markdown("---")
    select_all      = st.toggle("Select All Stocks", value=True)
    current_default = all_stocks if select_all else []
    selected_stocks = st.multiselect("Active Stocks", all_stocks, default=current_default)

    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years  = st.multiselect("Years", available_years, default=available_years[:2])


# ─────────────────────────────────────────────
# EARLY GUARDS
# ─────────────────────────────────────────────
if not selected_years:
    st.warning("⚠️ Please select at least one year.")
    st.stop()

if not selected_stocks:
    st.warning("⚠️ Please select at least one stock.")
    st.stop()

filtered_prices = prices_df[prices_df.index.year.isin(selected_years)][selected_stocks]

if filtered_prices.empty:
    st.warning("⚠️ No data for the selected filters.")
    st.stop()

df_sum = calc_summary(filtered_prices)

if df_sum.empty:
    st.warning("⚠️ Not enough data to compute returns. Each stock needs at least 2 price points.")
    st.stop()

avg_years = df_sum["_years"].mean()


# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
st.markdown(f'<h1 class="main-header">📈 {selected_file.replace(".xlsx", "")}</h1>', unsafe_allow_html=True)

sync_time = datetime.fromtimestamp(os.path.getmtime(file_path)).strftime("%Y-%m-%d %H:%M")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(
        f'<div class="info-chip">📅 <b>Period:</b> '
        f'{filtered_prices.index.min().strftime("%d %b %Y")} — '
        f'{filtered_prices.index.max().strftime("%d %b %Y")}</div>',
        unsafe_allow_html=True,
    )
with c2:
    st.markdown(
        f'<div class="info-chip">📊 <b>Sessions:</b> {len(filtered_prices)} Trading Days</div>',
        unsafe_allow_html=True,
    )
with c3:
    st.markdown(
        f'<div class="info-chip">🔄 <b>Last Sync:</b> {sync_time}</div>',
        unsafe_allow_html=True,
    )

st.markdown("<br>", unsafe_allow_html=True)

m1, m2, m3 = st.columns(3)
m1.metric("🏆 Top Performer",       f"{df_sum.iloc[0]['Return %']:.1f}%",  f"Stock: {df_sum.iloc[0]['Ticker']}")
m2.metric("📈 Selection Avg Return", f"{df_sum['Return %'].mean():.1f}%",  "Overall Portfolio")
m3.metric("📅 Avg Annualised CAGR",  f"{df_sum['CAGR %'].mean():.1f}%",    f"Over ~{avg_years:.1f} yrs (per stock)")

st.divider()


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
t1, t2, t3, t4, t5, t6 = st.tabs([
    "📊 Visuals",
    "📋 Performance Stats",
    "📅 Monthly Heatmap",
    "🏢 Quarterly Heatmap",
    "📆 Daily Heatmap",
    "🔍 Deep-Dive",
])


# ── TAB 1 ──────────────────────────────────────
with t1:
    v1, v2 = st.columns([1, 1.5])
    with v1:
        st.subheader("🔥 Performance Ranking")
        fig_bar = px.bar(
            df_sum, x="Return %", y="Ticker", orientation="h",
            color="Return %", color_continuous_scale="RdYlGn",
            template="plotly_white",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with v2:
        st.subheader("📈 Relative Price Movement")
        st.plotly_chart(
            px.line(filtered_prices, template="plotly_white"),
            use_container_width=True,
        )

    st.divider()

    # Normalised chart (rebased to 100)
    st.subheader("🔢 Normalised Chart (Rebased to 100)")
    first_valid = filtered_prices.apply(lambda c: c.dropna().iloc[0] if c.dropna().shape[0] else None)
    norm = filtered_prices.div(first_valid) * 100
    st.plotly_chart(px.line(norm, template="plotly_white", labels={"value": "Rebased Price (100 = start)"}), use_container_width=True)

    st.divider()
    st.subheader("🕵️ Rolling 12M Return Consistency")
    roll_raw = load_sheet(file_path, SHEET_ROLLING_12M)
    if roll_raw is not None:
        roll_raw.index = pd.to_datetime(roll_raw.index)
        roll_raw.rename(columns=name_map, inplace=True)
        # Only show stocks present in both
        cols_avail = [c for c in selected_stocks if c in roll_raw.columns]
        if cols_avail:
            display_roll = roll_raw[roll_raw.index.year.isin(selected_years)][cols_avail]
            fig_roll = px.line(display_roll, template="plotly_white")
            fig_roll.add_hline(y=0, line_dash="dash", line_color="red")
            st.plotly_chart(fig_roll, use_container_width=True)
        else:
            st.info("ℹ️ No matching tickers in rolling_12m sheet.")
    else:
        st.info("ℹ️ Rolling analysis unavailable. Run engine.py to sync.")


# ── TAB 2 ──────────────────────────────────────
with t2:
    st.subheader("Detailed Performance Metrics")
    display_df = df_sum.drop(columns=["_years"])
    st.dataframe(
        display_df.style
            .background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
            .format({"Return %": "{:.2f}%", "CAGR %": "{:.2f}%", "Latest": "₹{:.2f}"}),
        use_container_width=True,
        hide_index=True,
    )


# ── TAB 3 ──────────────────────────────────────
with t3:
    st.subheader("Monthly Returns (%)")
    m_data = load_sheet(file_path, SHEET_MONTHLY)
    if m_data is not None:
        m_data.rename(columns=name_map, inplace=True)
        m_data.index = pd.to_datetime(m_data.index)
        cols_avail = [c for c in selected_stocks if c in m_data.columns]
        if cols_avail:
            f_m = m_data[m_data.index.year.isin(selected_years)][cols_avail].sort_index(ascending=False)
            f_m.index = f_m.index.strftime("%Y-%b")
            st.dataframe(
                f_m.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"),
                use_container_width=True,
            )
        else:
            st.info("ℹ️ No matching tickers in monthly_returns sheet.")
    else:
        st.info("ℹ️ Monthly data not found.")


# ── TAB 4 ──────────────────────────────────────
with t4:
    st.subheader("Quarterly Returns (%)")
    q_data = load_sheet(file_path, SHEET_QUARTERLY)
    if q_data is not None:
        q_data.rename(columns=name_map, inplace=True)
        try:
            q_data.index = pd.to_datetime([str(x).replace("Q", "-") for x in q_data.index])
        except Exception:
            pass
        cols_avail = [c for c in selected_stocks if c in q_data.columns]
        if cols_avail:
            f_q = q_data[q_data.index.year.isin(selected_years)][cols_avail].sort_index(ascending=False)
            f_q.index = f_q.index.to_period("Q").astype(str)
            st.dataframe(
                f_q.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"),
                use_container_width=True,
            )
        else:
            st.info("ℹ️ No matching tickers in quarterly_returns sheet.")
    else:
        st.info("ℹ️ Quarterly data not found.")


# ── TAB 5 ──────────────────────────────────────
with t5:
    available_months = sorted(
        prices_df[prices_df.index.year.isin(selected_years)].index.strftime("%Y-%m").unique().tolist(),
        reverse=True,
    )
    default_month = [available_months[0]] if available_months else []
    sel_months = st.multiselect("📅 Select Month(s) to Analyse", available_months, default=default_month, key="d_month_selector")

    st.divider()

    if not sel_months:
        st.info("ℹ️ Select at least one month above.")
    else:
        try:
            # Use prices_df (full) for correct pct_change on boundary days,
            # but restrict COLUMNS to selected_stocks only — fixes the consistency bug
            daily_ret_full = prices_df[selected_stocks].pct_change() * 100
            target_indices = prices_df[prices_df.index.strftime("%Y-%m").isin(sel_months)].index

            if target_indices.empty:
                st.warning("⚠️ No data found for the selected months.")
            else:
                day_view = daily_ret_full.loc[target_indices].copy()

                summary_df = pd.DataFrame({
                    "Total Return (%)":   day_view.sum(),
                    "Best Day (%)":       day_view.max(),
                    "Worst Day (%)":      day_view.min(),
                    "Avg Daily Move (%)": day_view.mean(),
                }).sort_values("Total Return (%)", ascending=False)

                top_2_names = summary_df.head(2).index.tolist()

                # Insight tiles
                overall_winner = summary_df.index[0]
                overall_val    = summary_df.iloc[0]["Total Return (%)"]
                max_val        = day_view.max().max()
                best_s         = day_view.max().idxmax()
                best_d         = day_view[best_s].idxmax().strftime("%d %b %Y")
                min_val        = day_view.min().min()
                worst_s        = day_view.min().idxmin()
                worst_d        = day_view[worst_s].idxmin().strftime("%d %b %Y")

                ti1, ti2, ti3 = st.columns(3)
                ti1.metric("🥇 Period Leader",    f"{overall_val:.2f}%", overall_winner)
                ti2.metric("🚀 Top Daily Move",   f"{max_val:.2f}%",     f"{best_s} ({best_d})")
                ti3.metric("📉 Deepest Day Cut",  f"{min_val:.2f}%",     f"{worst_s} ({worst_d})")

                # Summary table
                st.subheader("📊 Performance Ranking (Selected Period)")
                st.dataframe(
                    summary_df.style.background_gradient(cmap="YlGn", subset=["Total Return (%)"]).format("{:.2f}%"),
                    use_container_width=True,
                )

                # Trend chart
                chart_col, ctrl_col = st.columns([4, 1])
                with ctrl_col:
                    st.write("🔍 **Chart Filters**")
                    sel_stocks_chart = st.multiselect(
                        "Select Stocks:", selected_stocks, default=top_2_names, key="t5_trend_chart_stocks"
                    )
                    st.caption("Winners auto-selected.")

                with chart_col:
                    if sel_stocks_chart:
                        st.subheader(f"🕵️ Compounded Growth ({', '.join(sel_months)})")
                        chart_data     = day_view[sel_stocks_chart].copy()
                        cum_trend_pct  = ((1 + chart_data / 100).cumprod() - 1) * 100
                        fig_trend      = px.line(
                            cum_trend_pct, template="plotly_white",
                            labels={"value": "Growth %", "index": "Date"},
                            markers=True, height=450,
                        )
                        fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
                        fig_trend.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
                        st.plotly_chart(fig_trend, use_container_width=True)

                # Raw daily heatmap
                st.subheader("📋 Raw Daily Returns (%)")
                table_display = day_view.copy().sort_index(ascending=False)
                table_display.index = table_display.index.strftime("%Y-%m-%d (%a)")
                st.dataframe(
                    table_display.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"),
                    use_container_width=True,
                )

                # Price history
                st.subheader("📈 Absolute Price History (Selected Period)")
                period_prices = prices_df.loc[target_indices, selected_stocks].copy()
                period_prices.index = period_prices.index.strftime("%Y-%m-%d")
                st.dataframe(period_prices.sort_index(ascending=False), use_container_width=True)

                # Downloads
                st.divider()
                dl1, dl2 = st.columns(2)
                with dl1:
                    st.download_button(
                        "📥 Download Daily Returns (CSV)",
                        data=day_view.to_csv().encode("utf-8"),
                        file_name=f"returns_{'_'.join(sel_months)}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="dl_ret_t5",
                    )
                with dl2:
                    st.download_button(
                        "📥 Download Price History (CSV)",
                        data=period_prices.to_csv().encode("utf-8"),
                        file_name=f"prices_{'_'.join(sel_months)}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="dl_prices_t5",
                    )

        except Exception as e:
            st.error(f"⚠️ Tab 5 Error: {e}")


# ── TAB 6 ──────────────────────────────────────
with t6:
    st.subheader("🔍 Individual Stock Deep-Dive")
    target_stock = st.selectbox("Pick a stock to analyse:", selected_stocks, key="deep_dive_ticker")

    if target_stock:
        s_data      = filtered_prices[target_stock].dropna()
        full_series = prices_df[target_stock].dropna()

        # MAs computed on full series, then aligned — use reindex to avoid silent drops
        ma50  = full_series.rolling(50).mean().reindex(s_data.index)
        ma200 = full_series.rolling(200).mean().reindex(s_data.index)

        last_ma50  = ma50.dropna().iloc[-1]  if not ma50.dropna().empty  else None
        last_ma200 = ma200.dropna().iloc[-1] if not ma200.dropna().empty else None

        # Signal + days-since-crossover
        if last_ma50 is not None and last_ma200 is not None:
            cross_series = (ma50 > ma200).dropna()
            if cross_series.empty:
                st.info("ℹ️ Not enough data to determine crossover.")
            else:
                current_bullish = cross_series.iloc[-1]
                # Find last regime change
                regime_change   = cross_series[cross_series != cross_series.shift(1)]
                days_since      = (s_data.index[-1] - regime_change.index[-1]).days if len(regime_change) > 0 else None
                days_txt        = f" · {days_since}d ago" if days_since is not None else ""
                if current_bullish:
                    st.success(f"🚀 **Bullish Trend:** Golden Cross active{days_txt}")
                else:
                    st.error(f"⚠️ **Bearish Trend:** Death Cross active{days_txt}")
        else:
            st.info("ℹ️ Insufficient MA data for signal.")

        # Metric cards
        dd   = (s_data / s_data.cummax() - 1) * 100
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price",  f"₹{s_data.iloc[-1]:.2f}")
        c2.metric("Period Return",  f"{((s_data.iloc[-1]/s_data.iloc[0])-1)*100:.2f}%")
        c3.metric("Max Price",      f"₹{s_data.max():.2f}", f"Peak: {s_data.idxmax().strftime('%d %b %Y')}")
        c4.metric("Max Drawdown",   f"{dd.min():.2f}%", delta_color="inverse")

        # Technical chart
        fig_main = go.Figure()
        fig_main.add_trace(go.Scatter(x=s_data.index, y=s_data,     name=target_stock, line=dict(color=BRAND_DARK, width=2)))
        fig_main.add_trace(go.Scatter(x=ma50.index,   y=ma50,       name="50 DMA",     line=dict(dash="dash",  color="orange", width=1.5)))
        fig_main.add_trace(go.Scatter(x=ma200.index,  y=ma200,      name="200 DMA",    line=dict(dash="dot",   color="red",    width=1.5)))
        fig_main.add_annotation(
            x=s_data.idxmax(), y=s_data.max(),
            text="Cycle Peak", showarrow=True, arrowhead=2, font=dict(color=BRAND_DARK),
        )
        fig_main.update_layout(template="plotly_white", title=f"{target_stock} — Technical Trend", hovermode="x unified")
        st.plotly_chart(fig_main, use_container_width=True)

        col_l, col_r = st.columns(2)
        with col_l:
            st.plotly_chart(
                px.area(dd, title="Peak-to-Trough Drawdown (%)", template="plotly_white", color_discrete_sequence=["#ff4b4b"]),
                use_container_width=True,
            )
        with col_r:
            daily_ret = s_data.pct_change() * 100
            st.plotly_chart(
                px.histogram(daily_ret, nbins=40, title="Daily Return Distribution (%)", template="plotly_white"),
                use_container_width=True,
            )

        # Correlation with other stocks (bonus insight)
        if len(selected_stocks) > 1:
            st.subheader(f"🔗 {target_stock} — Correlation with Other Selected Stocks")
            corr_data = filtered_prices.pct_change().dropna()
            corr_vals = corr_data.corr()[target_stock].drop(target_stock).sort_values(ascending=False)
            fig_corr  = px.bar(
                corr_vals, orientation="h", template="plotly_white",
                color=corr_vals.values, color_continuous_scale="RdYlGn",
                labels={"value": "Correlation", "index": "Stock"},
                title=f"Return Correlation with {target_stock}",
                range_color=[-1, 1],
            )
            st.plotly_chart(fig_corr, use_container_width=True)
