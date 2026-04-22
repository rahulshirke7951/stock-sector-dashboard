import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────
FOLDER            = "dashboards"
SHEET_PRICES      = "prices"
SHEET_METADATA    = "metadata"
SHEET_ROLLING_12M = "rolling_12m"
SHEET_MONTHLY     = "monthly_returns"
SHEET_QUARTERLY   = "quarterly_returns"

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

.filter-badge {{
    font-family: 'DM Mono', monospace;
    font-size: 0.72em;
    color: #fff;
    background: {BRAND_MID};
    padding: 4px 12px;
    border-radius: 20px;
    display: inline-block;
    margin: 2px 4px;
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
    """Returns RAW prices with original ticker columns — never rename in-place here."""
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

def apply_name_map(df: pd.DataFrame, name_map: dict) -> pd.DataFrame:
    return df.rename(columns=name_map)

@st.cache_data(show_spinner=False)
def compute_corr(_df: pd.DataFrame) -> pd.DataFrame:
    return _df.pct_change().dropna().corr()

def opportunity_engine(price_df: pd.DataFrame) -> pd.DataFrame:
    results = []

    for stock in price_df.columns:
        p = price_df[stock].dropna()

        if len(p) < 220:
            continue

        ma50 = p.rolling(50).mean()
        ma200 = p.rolling(200).mean()

        rolling_high = p.rolling(50).max()
        drawdown = (p / rolling_high - 1) * 100
        momentum = p.pct_change(21) * 100

        latest_price = p.iloc[-1]
        latest_ma50 = ma50.iloc[-1]
        latest_ma200 = ma200.iloc[-1]
        latest_drawdown = drawdown.iloc[-1]
        latest_momentum = momentum.iloc[-1]

        trend_strong = latest_price > latest_ma200
        pullback_ok = -15 < latest_drawdown < -5
        support_holding = latest_price >= latest_ma50

        if trend_strong and pullback_ok and support_holding:

            strength = (
                "Strong" if latest_momentum > 2 else
                "Moderate" if latest_momentum > 0 else
                "Weak"
            )

            message = (
                f"🟢 BUY SETUP\n"
                f"Pullback: {latest_drawdown:.1f}%\n"
                f"Trend intact (above 50 & 200 DMA)\n"
                f"Momentum: {strength}\n"
                f"→ Accumulate"
            )

            results.append({
                "Stock": stock,
                "Price": round(latest_price, 2),
                "Drawdown %": round(latest_drawdown, 2),
                "Momentum %": round(latest_momentum, 2),
                "Strength": strength,
                "Signal": "BUY 🟢",
                "Action": "Accumulate",
                "Message": message
            })

    if not results:
        return pd.DataFrame()

    return pd.DataFrame(results).sort_values("Drawdown %", ascending=False)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────
def calc_summary(filtered_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for ticker in filtered_df.columns:
        col = filtered_df[ticker].dropna()
        if len(col) < 2:
            continue
        daily_ret = col.pct_change().dropna()
        days  = (col.index[-1] - col.index[0]).days
        yrs   = max(days / 365.25, 0.1)
        ret   = ((col.iloc[-1] / col.iloc[0]) - 1) * 100
        cagr  = (((col.iloc[-1] / col.iloc[0]) ** (1 / yrs)) - 1) * 100
        vol   = daily_ret.std() * np.sqrt(252) * 100 if len(daily_ret) > 1 else np.nan
        sharpe = (cagr / vol) if (not np.isnan(vol) and vol > 0) else np.nan
        rows.append({
            "Ticker":      ticker,
            "Return %":    ret,
            "CAGR %":      cagr,
            "Ann. Vol %":  vol,
            "Sharpe":      sharpe,
            "Latest":      col.iloc[-1],
            "_years":      yrs,
        })
    return pd.DataFrame(rows).sort_values("Return %", ascending=False)


def parse_quarterly_index(raw_index) -> pd.DatetimeIndex:
    parsed = []
    for x in raw_index:
        s = str(x).strip()
        try:
            if any(c.isdigit() for c in s) and ("/" in s or (s.count("-") >= 2) or len(s) > 7):
                ts = pd.to_datetime(s)
                parsed.append(ts.to_period("Q").to_timestamp())
                continue
            s_norm = s.replace("-", "").replace(" ", "")
            if s_norm[:1] == "Q":
                q = int(s_norm[1])
                y = int(s_norm[2:])
            else:
                y = int(s_norm[:4])
                q = int(s_norm[5])
            month = (q - 1) * 3 + 1
            parsed.append(pd.Timestamp(year=y, month=month, day=1))
        except Exception:
            parsed.append(pd.NaT)
    return pd.DatetimeIndex(parsed)


def non_contiguous_years(years: list) -> bool:
    s = sorted(years)
    return any(s[i + 1] - s[i] > 1 for i in range(len(s) - 1))


def current_quarter_start() -> pd.Timestamp:
    """Returns the first day of the current quarter."""
    today = pd.Timestamp.today().normalize()
    return today.to_period("Q").to_timestamp()


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

    # FIX #1: Use a session_state flag to trigger rerun AFTER the callback completes.
    # st.rerun() inside on_change is a no-op in Streamlit — the flag approach is the correct pattern.
    def _on_file_change():
        """Set a flag; the main script body will call st.rerun() after this callback returns."""
        st.cache_data.clear()
        st.session_state["_needs_rerun"] = True

    selected_file = st.selectbox(
        "Select Watchlist", files,
        key="main_file_select",
        on_change=_on_file_change,
    )
    file_path = os.path.join(FOLDER, selected_file)

    if st.button(
        "🔄 Refresh Price Data",
        use_container_width=True,
        type="primary",
        help="Use this ONLY after running your engine to pull fresh market data. Switching watchlists above is fully automatic — no refresh needed.",
    ):
        st.cache_data.clear()
        st.rerun()

    name_map  = load_name_map(file_path)
    _raw_prices = load_prices(file_path)
    prices_df   = apply_name_map(_raw_prices, name_map)
    all_stocks  = sorted(prices_df.columns.tolist())

    st.markdown("---")

    select_all      = st.toggle("Select All Stocks", value=True)
    current_default = all_stocks if select_all else []
    selected_stocks = st.multiselect(
        "Active Stocks",
        all_stocks,
        default=current_default,
        key=f"stocks_{selected_file}_{select_all}",
    )


    if selected_stocks:
        st.caption(f"✅ {len(selected_stocks)} of {len(all_stocks)} stocks selected")

    available_years = sorted(prices_df.index.year.unique(), reverse=True)
    selected_years  = st.multiselect("Years", available_years, default=available_years[:2])

    if len(selected_years) > 1 and non_contiguous_years(selected_years):
        st.warning(
            "⚠️ **Non-contiguous years selected.**\n\n"
            "CAGR is computed across the full gap including missing years — "
            "this will overstate annualised returns. Use consecutive years for accurate CAGR."
        )

    st.markdown("---")
    st.markdown("**📌 Benchmark (optional)**")
    benchmark_label = st.text_input(
        "Benchmark ticker (must be a column in your file)",
        value="", placeholder="e.g. NIFTY50", key="benchmark_input",
    )
    benchmark = benchmark_label.strip() if benchmark_label.strip() in prices_df.columns else None
    if benchmark_label.strip() and benchmark is None:
        st.caption("⚠️ Ticker not found in loaded data.")


# ─────────────────────────────────────────────
# AUTO-RERUN TRIGGER (watchlist switch)
# ─────────────────────────────────────────────
# st.rerun() is a no-op inside callbacks, so _on_file_change() sets a flag instead.
# We check it here in the main script body where st.rerun() works correctly.
if st.session_state.pop("_needs_rerun", False):
    st.rerun()

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
ranking_order = df_sum["Ticker"].tolist()

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

year_str   = ", ".join(str(y) for y in sorted(selected_years))
bm_badge   = f'<span class="filter-badge">📌 {benchmark}</span>' if benchmark else ""
badge_html = (
    f'<div style="text-align:center;margin-top:10px;">'
    f'<span class="filter-badge">📂 {selected_file.replace(".xlsx","")}</span>'
    f'<span class="filter-badge">📅 {year_str}</span>'
    f'<span class="filter-badge">🧮 {len(selected_stocks)} stocks</span>'
    f'{bm_badge}'
    f'</div>'
)
st.markdown(badge_html, unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

m1, m2, m3, m4 = st.columns(4)
m1.metric("🏆 Top Performer",       f"{df_sum.iloc[0]['Return %']:.1f}%",  f"Stock: {df_sum.iloc[0]['Ticker']}")
m2.metric("📈 Avg Return",          f"{df_sum['Return %'].mean():.1f}%",   "Selection average")
m3.metric("📅 Avg CAGR",            f"{df_sum['CAGR %'].mean():.1f}%",     f"~{avg_years:.1f} yrs/stock")
m4.metric("📉 Avg Ann. Volatility", f"{df_sum['Ann. Vol %'].mean():.1f}%", "Annualised (252d)")

st.divider()


# ─────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────
t1, t2, t3, t4, t5, t6, t7 = st.tabs([
    "📊 Visuals",
    "📋 Performance Stats",
    "📅 Monthly Heatmap",
    "🏢 Quarterly Heatmap",
    "📆 Daily Heatmap",
    "🔍 Deep-Dive",
    "🟢 Opportunities"
])


# ══════════════════════════════════════════════
# TAB 1 — VISUALS
# ══════════════════════════════════════════════
with t1:
    v1, v2 = st.columns([1, 1.5])

    with v1:
        st.subheader("🔥 Performance Ranking")
        bar_df = df_sum.copy()
        bar_df["Direction"] = bar_df["Return %"].apply(lambda x: "Positive ▲" if x >= 0 else "Negative ▼")
        fig_bar = px.bar(
            bar_df, x="Return %", y="Ticker", orientation="h",
            color="Direction",
            color_discrete_map={"Positive ▲": "#2ecc71", "Negative ▼": "#e74c3c"},
            template="plotly_white",
        )
        fig_bar.update_layout(showlegend=True, legend_title_text="")
        st.plotly_chart(fig_bar, use_container_width=True)

    with v2:
        st.subheader("📈 Relative Price Movement")
        fig_price = px.line(filtered_prices, template="plotly_white")
        if benchmark and benchmark in prices_df.columns:
            bm_series = prices_df[benchmark][prices_df.index.year.isin(selected_years)]
            fig_price.add_trace(go.Scatter(
                x=bm_series.index, y=bm_series,
                name=f"📌 {benchmark}",
                line=dict(color="black", width=2, dash="dot"),
            ))
        st.plotly_chart(fig_price, use_container_width=True)

    st.divider()

    st.subheader("🔢 Normalised Chart (Rebased to 100)")
    st.caption(
        "💡 **What is Rebased Price?** Every stock starts at 100 on the first day of the selected period — "
        "regardless of its actual price. A value of 115 means +15% from your entry; 87 means −13%. "
        "This removes price-level bias and lets you fairly compare stocks trading at very different absolute prices (e.g. ₹50 vs ₹5,000)."
    )
    first_valid = filtered_prices.apply(lambda c: c.dropna().iloc[0] if c.dropna().shape[0] else None)
    norm        = filtered_prices.div(first_valid) * 100
    fig_norm    = px.line(norm, template="plotly_white", labels={"value": "Rebased Price (100 = start)"})

    if benchmark and benchmark in prices_df.columns:
        bm_series = prices_df[benchmark][prices_df.index.year.isin(selected_years)].dropna()
        if not bm_series.empty:
            bm_norm = bm_series / bm_series.iloc[0] * 100
            fig_norm.add_trace(go.Scatter(
                x=bm_norm.index, y=bm_norm,
                name=f"📌 {benchmark}",
                line=dict(color="black", width=2, dash="dot"),
            ))
    st.plotly_chart(fig_norm, use_container_width=True)

    st.divider()

    st.subheader("🕵️ Rolling 12M Return Consistency")
    roll_raw = load_sheet(file_path, SHEET_ROLLING_12M)
    if roll_raw is not None:
        roll_raw.index = pd.to_datetime(roll_raw.index)
        roll_raw = apply_name_map(roll_raw, name_map)
        cols_avail = [c for c in selected_stocks if c in roll_raw.columns]
        if cols_avail:
            display_roll = roll_raw[cols_avail]
            fig_roll = px.line(display_roll, template="plotly_white",
                               labels={"value": "12M Rolling Return (%)"})
            fig_roll.add_hline(
                y=0, line_dash="dash", line_color="red",
                annotation_text="Breakeven (0%)",
                annotation_position="bottom right",
            )
            st.plotly_chart(fig_roll, use_container_width=True)
        else:
            st.info("ℹ️ No matching tickers in rolling_12m sheet.")
    else:
        st.info("ℹ️ Rolling analysis unavailable. Run engine.py to sync.")


# ══════════════════════════════════════════════
# TAB 2 — PERFORMANCE STATS
# ══════════════════════════════════════════════
with t2:
    st.subheader("Detailed Performance Metrics")
    display_df = df_sum.drop(columns=["_years"])

    st.dataframe(
        display_df.style
            .background_gradient(subset=["Return %", "CAGR %"], cmap="RdYlGn")
            .background_gradient(subset=["Ann. Vol %"],          cmap="RdYlGn_r")
            .background_gradient(subset=["Sharpe"],              cmap="RdYlGn")
            .format({
                "Return %":   "{:.2f}%",
                "CAGR %":     "{:.2f}%",
                "Ann. Vol %": "{:.2f}%",
                "Sharpe":     "{:.2f}",
                "Latest":     "₹{:.2f}",
            }),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.subheader("🔗 Full Correlation Matrix")
    if len(selected_stocks) > 1:
        corr_matrix = compute_corr(filtered_prices)
        fig_heatmap = px.imshow(
            corr_matrix,
            color_continuous_scale="RdYlGn",
            zmin=-1, zmax=1,
            text_auto=".2f",
            aspect="auto",
            template="plotly_white",
            title="Pairwise Return Correlation (based on daily % returns)",
        )
        fig_heatmap.update_layout(coloraxis_colorbar_title="r")
        st.plotly_chart(fig_heatmap, use_container_width=True)
    else:
        st.info("ℹ️ Select 2 or more stocks to enable the correlation heatmap.")


# ══════════════════════════════════════════════
# TAB 3 — MONTHLY HEATMAP
# ══════════════════════════════════════════════
with t3:
    st.subheader("Monthly Returns (%)")
    sort_monthly = st.toggle("Sort by Performance", value=True, key="sort_monthly")
    m_data = load_sheet(file_path, SHEET_MONTHLY)
    if m_data is not None:
        m_data = apply_name_map(m_data, name_map)
        m_data.index = pd.to_datetime(m_data.index)
        cols_avail = [c for c in selected_stocks if c in m_data.columns]
        if cols_avail:
            f_m = m_data[m_data.index.year.isin(selected_years)][cols_avail].sort_index(ascending=False)
            # 🔥 Apply ranking order if toggle ON
            if sort_monthly:
                ordered_cols = [c for c in ranking_order if c in f_m.columns]
                f_m = f_m[ordered_cols]
            f_m.index = f_m.index.strftime("%Y-%b")
            st.dataframe(
                f_m.style.background_gradient(cmap="RdYlGn", axis=None).format("{:.2f}%"),
                use_container_width=True,
            )
        else:
            st.info("ℹ️ No matching tickers in monthly_returns sheet.")
    else:
        st.info("ℹ️ Monthly data not found.")


# ══════════════════════════════════════════════
# TAB 4 — QUARTERLY HEATMAP
# ══════════════════════════════════════════════
with t4:
    st.subheader("Quarterly Returns (%)")
    sort_quarterly = st.toggle("Sort by Performance", value=True, key="sort_quarterly")
    q_data = load_sheet(file_path, SHEET_QUARTERLY)
    if q_data is not None:
        q_data = apply_name_map(q_data, name_map)
        q_data.index = parse_quarterly_index(q_data.index)
        q_data = q_data[q_data.index.notna()]

        cols_avail = [c for c in selected_stocks if c in q_data.columns]
        if cols_avail:
            
            f_q = q_data[q_data.index.year.isin(selected_years)][cols_avail].sort_index(ascending=False)
            # 🔥 Apply ranking order if toggle ON
            if sort_quarterly:
                ordered_cols = [c for c in ranking_order if c in f_q.columns]
                f_q = f_q[ordered_cols]

            

            # FIX #2: Cap the expected quarter grid at the CURRENT quarter — never show future quarters.
            # e.g. if today is in Q1 2026, grid ends at Q1 2026, not Q4 2026.
            today_quarter_start = current_quarter_start()
            grid_end = min(
                pd.Timestamp(year=max(selected_years), month=10, day=1),  # Q4 start of max year
                today_quarter_start,                                        # current quarter start
            )

            expected_quarters = pd.period_range(
                start=f"{min(selected_years)}Q1",
                end=pd.Period(grid_end, freq="Q"),
                freq="Q",
            )
            expected_idx = expected_quarters.to_timestamp()
            f_q = f_q.reindex(expected_idx.sort_values(ascending=False))
            f_q.index = f_q.index.to_period("Q").astype(str)

            st.dataframe(
                f_q.style
                    .background_gradient(cmap="RdYlGn", axis=None)
                    .format("{:.2f}%", na_rep="—"),
                use_container_width=True,
            )
            missing_count = f_q.isna().all(axis=1).sum()
            if missing_count:
                st.caption(f"ℹ️ {missing_count} quarter(s) show '—' because no data exists in the source file for those periods.")
        else:
            st.info("ℹ️ No matching tickers in quarterly_returns sheet.")
    else:
        st.info("ℹ️ Quarterly data not found.")


# ══════════════════════════════════════════════
# TAB 5 — DAILY HEATMAP
# ══════════════════════════════════════════════
with t5:
    sort_daily = st.toggle("Sort by Performance", value=True, key="sort_daily")
    available_months = sorted(
        prices_df[prices_df.index.year.isin(selected_years)].index.strftime("%Y-%m").unique().tolist(),
        reverse=True,
    )
    default_month = [available_months[0]] if available_months else []
    sel_months    = st.multiselect(
        "📅 Select Month(s) to Analyse",
        available_months,
        default=default_month,
        key="d_month_selector",
    )

    st.divider()

    if not sel_months:
        st.info("ℹ️ Select at least one month above.")
    else:
        with st.spinner("Crunching daily returns…"):
            try:
                target_indices = prices_df[
                    prices_df.index.strftime("%Y-%m").isin(sel_months)
                ].index

                if target_indices.empty:
                    st.warning("⚠️ No data found for the selected months.")
                else:

                     # 🔥 Decide column order FIRST (OUTSIDE)
                if sort_daily:
                    ordered_cols = [c for c in ranking_order if c in selected_stocks]
                else:
                    ordered_cols = selected_stocks
                
                # ✅ Now compute returns
                daily_ret_full = (
                    prices_df[ordered_cols]
                    .loc[:target_indices[-1]]
                    .pct_change() * 100
                )   
                  
                    day_view = daily_ret_full.loc[target_indices].copy()

                    summary_df = pd.DataFrame({
                        "Total Return (%)":   ((1 + day_view / 100).prod() - 1) * 100,
                        "Best Day (%)":       day_view.max(),
                        "Worst Day (%)":      day_view.min(),
                        "Avg Daily Move (%)": day_view.mean(),
                    }).sort_values("Total Return (%)", ascending=False)

                    top_2_names    = summary_df.head(2).index.tolist()
                    overall_winner = summary_df.index[0]
                    overall_val    = summary_df.iloc[0]["Total Return (%)"]
                    max_val        = day_view.max().max()
                    best_s         = day_view.max().idxmax()
                    best_d         = day_view[best_s].idxmax().strftime("%d %b %Y")
                    min_val        = day_view.min().min()
                    worst_s        = day_view.min().idxmin()
                    worst_d        = day_view[worst_s].idxmin().strftime("%d %b %Y")

                    ti1, ti2, ti3 = st.columns(3)
                    ti1.metric("🥇 Period Leader",   f"{overall_val:.2f}%", overall_winner)
                    ti2.metric("🚀 Top Daily Move",  f"{max_val:.2f}%",     f"{best_s} ({best_d})")
                    ti3.metric("📉 Deepest Day Cut", f"{min_val:.2f}%",     f"{worst_s} ({worst_d})")

                    st.subheader("📊 Performance Ranking — Compounded (Selected Period)")
                    st.caption("ℹ️ 'Total Return' uses compounded daily returns, not arithmetic sum.")
                    st.dataframe(
                        summary_df.style
                            .background_gradient(cmap="YlGn", subset=["Total Return (%)"])
                            .format("{:.2f}%"),
                        use_container_width=True,
                    )

                    chart_col, ctrl_col = st.columns([4, 1])
                    with ctrl_col:
                        st.write("🔍 **Chart Filters**")
                        sel_stocks_chart = st.multiselect(
                            "Select Stocks:", selected_stocks, default=top_2_names,
                            key="t5_trend_chart_stocks",
                        )
                        st.caption("Winners auto-selected.")

                    with chart_col:
                        if sel_stocks_chart:
                            st.subheader(f"🕵️ Compounded Growth ({', '.join(sel_months)})")
                            chart_data    = day_view[sel_stocks_chart].copy()
                            cum_trend_pct = ((1 + chart_data / 100).cumprod() - 1) * 100
                            fig_trend     = px.line(
                                cum_trend_pct, template="plotly_white",
                                labels={"value": "Growth %", "index": "Date"},
                                markers=True, height=450,
                            )
                            fig_trend.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.7)
                            fig_trend.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=10, b=0))
                            st.plotly_chart(fig_trend, use_container_width=True)

                    st.subheader("📋 Raw Daily Returns (%)")
                    table_display = day_view.copy().sort_index(ascending=False)
                    table_display.index = table_display.index.strftime("%Y-%m-%d (%a)")
                    st.dataframe(
                        table_display.style
                            .background_gradient(cmap="RdYlGn", axis=None)
                            .format("{:.2f}%"),
                        use_container_width=True,
                    )

                    st.subheader("📈 Absolute Price History (Selected Period)")
                    period_prices = prices_df.loc[target_indices, ordered_cols].copy()
                    period_prices.index = period_prices.index.strftime("%Y-%m-%d")
                    st.dataframe(period_prices.sort_index(ascending=False), use_container_width=True)

                    month_key = "_".join(sel_months)
                    st.divider()
                    dl1, dl2 = st.columns(2)
                    with dl1:
                        st.download_button(
                            "📥 Download Daily Returns (CSV)",
                            data=day_view.to_csv().encode("utf-8"),
                            file_name=f"returns_{month_key}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"dl_ret_{month_key}",
                        )
                    with dl2:
                        st.download_button(
                            "📥 Download Price History (CSV)",
                            data=period_prices.to_csv().encode("utf-8"),
                            file_name=f"prices_{month_key}.csv",
                            mime="text/csv",
                            use_container_width=True,
                            key=f"dl_prices_{month_key}",
                        )

            except Exception as e:
                st.error(f"⚠️ Tab 5 Error: {e}")


# ══════════════════════════════════════════════
# TAB 6 — DEEP-DIVE
# ══════════════════════════════════════════════
with t6:
    st.subheader("🔍 Individual Stock Deep-Dive")

    dd_col1, dd_col2 = st.columns([2, 1])
    with dd_col1:
        # 🔥 Apply ranking order
        ordered_stocks = [s for s in ranking_order if s in selected_stocks]
        
        # fallback safety (in case mismatch)
        if not ordered_stocks:
            ordered_stocks = selected_stocks
        
        target_stock = st.selectbox(
            "Primary stock:",
            ordered_stocks,
            key="deep_dive_ticker"
        )

    
    with dd_col2:
        compare_options = ["— None —"] + [
            s for s in ordered_stocks if s != target_stock
        ]
        
        compare_raw     = st.selectbox("Compare with:", compare_options, key="deep_dive_compare")
        compare_stock   = None if compare_raw == "— None —" else compare_raw

    if target_stock:
        with st.spinner(f"Loading analysis for {target_stock}…"):
            s_data      = filtered_prices[target_stock].dropna()
            full_series = prices_df[target_stock].dropna()

            ma50  = full_series.rolling(50).mean().reindex(s_data.index)
            ma200 = full_series.rolling(200).mean().reindex(s_data.index)

            ma50_valid  = ma50.dropna()
            ma200_valid = ma200.dropna()
            last_ma50   = ma50_valid.iloc[-1]  if not ma50_valid.empty  else None
            last_ma200  = ma200_valid.iloc[-1] if not ma200_valid.empty else None

            if last_ma50 is not None and last_ma200 is not None:
                cross_series = (ma50 > ma200).dropna()
                if not cross_series.empty:
                    current_bullish = cross_series.iloc[-1]
                    regime_change   = cross_series[cross_series != cross_series.shift(1)]
                    days_since      = (s_data.index[-1] - regime_change.index[-1]).days if len(regime_change) > 0 else None
                    days_txt        = f" · {days_since}d ago" if days_since is not None else ""
                    if current_bullish:
                        st.success(f"🚀 **Bullish Trend:** Golden Cross active{days_txt}")
                    else:
                        st.error(f"⚠️ **Bearish Trend:** Death Cross active{days_txt}")
            else:
                missing = []
                if last_ma50  is None: missing.append("50 DMA (needs ≥50 data points)")
                if last_ma200 is None: missing.append("200 DMA (needs ≥200 data points)")
                st.warning(
                    f"⚠️ Insufficient data for: {', '.join(missing)}. "
                    "Extend your year filter to enable MA signals."
                )

            dd_period  = (s_data / s_data.cummax() - 1) * 100
            dd_alltime = (full_series / full_series.cummax() - 1) * 100

            daily_ret_stock = s_data.pct_change().dropna()
            period_vol      = daily_ret_stock.std() * np.sqrt(252) * 100

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Current Price",        f"₹{s_data.iloc[-1]:.2f}")
            c2.metric("Period Return",         f"{((s_data.iloc[-1]/s_data.iloc[0])-1)*100:.2f}%")
            c3.metric("Max Price (Period)",    f"₹{s_data.max():.2f}", f"Peak: {s_data.idxmax().strftime('%d %b %Y')}")
            c4.metric("Period Max Drawdown",   f"{dd_period.min():.2f}%",    delta_color="inverse")
            c5.metric("All-Time Max Drawdown", f"{dd_alltime.min():.2f}%",   delta_color="inverse")

            fig_main = go.Figure()
            fig_main.add_trace(go.Scatter(
                x=s_data.index, y=s_data,
                name=target_stock, line=dict(color=BRAND_DARK, width=2),
            ))
            if not ma50_valid.empty:
                fig_main.add_trace(go.Scatter(
                    x=ma50.index, y=ma50, name="50 DMA",
                    line=dict(dash="dash", color="orange", width=1.5),
                ))
            if not ma200_valid.empty:
                fig_main.add_trace(go.Scatter(
                    x=ma200.index, y=ma200, name="200 DMA",
                    line=dict(dash="dot", color="red", width=1.5),
                ))
            if compare_stock and compare_stock in filtered_prices.columns:
                cs_data = filtered_prices[compare_stock].dropna()
                cs_scaled = cs_data / cs_data.iloc[0] * s_data.iloc[0]
                fig_main.add_trace(go.Scatter(
                    x=cs_scaled.index, y=cs_scaled,
                    name=f"⚖️ {compare_stock} (scaled)",
                    line=dict(color="#9b59b6", width=1.5, dash="dashdot"),
                ))
            fig_main.add_annotation(
                x=s_data.idxmax(), y=s_data.max(),
                text="Cycle Peak", showarrow=True, arrowhead=2, font=dict(color=BRAND_DARK),
            )
            fig_main.update_layout(
                template="plotly_white",
                title=f"{target_stock} — Technical Trend",
                hovermode="x unified",
            )
            st.plotly_chart(fig_main, use_container_width=True)

            col_l, col_r = st.columns(2)
            with col_l:
                fig_dd = go.Figure()
                fig_dd.add_trace(go.Scatter(
                    x=dd_period.index, y=dd_period,
                    fill="tozeroy", name="Period Drawdown",
                    line=dict(color="#ff4b4b"),
                ))
                fig_dd.add_trace(go.Scatter(
                    x=dd_alltime.index, y=dd_alltime,
                    name="All-Time Drawdown",
                    line=dict(color="#c0392b", dash="dot", width=1),
                ))
                fig_dd.update_layout(
                    template="plotly_white",
                    title="Drawdown: Period (filled) vs All-Time (dotted)",
                    hovermode="x unified",
                )
                st.plotly_chart(fig_dd, use_container_width=True)

            with col_r:
                fig_hist = px.histogram(
                    daily_ret_stock, nbins=40,
                    title=f"Daily Return Distribution — Ann. Vol: {period_vol:.1f}%",
                    template="plotly_white",
                )
                fig_hist.add_vline(
                    x=daily_ret_stock.mean(), line_dash="dash", line_color=BRAND_DARK,
                    annotation_text=f"Mean: {daily_ret_stock.mean():.2f}%",
                    annotation_position="top right",
                )
                st.plotly_chart(fig_hist, use_container_width=True)

            if len(selected_stocks) > 1:
                st.subheader(f"🔗 {target_stock} — Correlation with Other Stocks")
                corr_matrix = compute_corr(filtered_prices)
                if target_stock in corr_matrix.columns:
                    corr_vals = corr_matrix[target_stock].drop(target_stock).sort_values(ascending=False)
                    fig_corr  = px.bar(
                        corr_vals, orientation="h", template="plotly_white",
                        color=corr_vals.values, color_continuous_scale="RdYlGn",
                        labels={"value": "Correlation", "index": "Stock"},
                        title=f"Return Correlation with {target_stock}",
                        range_color=[-1, 1],
                    )
                    st.plotly_chart(fig_corr, use_container_width=True)
            else:
                st.info("ℹ️ Select 2 or more stocks to enable correlation analysis.")

# ══════════════════════════════════════════════
# TAB 7 — OPPORTUNITIES
# ══════════════════════════════════════════════
with t7:
    st.subheader("🟢 Buy Opportunities (Pullback in Strong Trend)")

    with st.spinner("Scanning market for opportunities…"):
        op_df = opportunity_engine(filtered_prices)

    if op_df.empty:
        st.info("ℹ️ No strong opportunities right now.")
    else:
        st.success(f"🔥 {len(op_df)} opportunity(ies) found")

        st.dataframe(
            op_df.drop(columns=["Message"]),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        # 🔍 Message Viewer
        selected_stock = st.selectbox(
            "🔍 View Opportunity Insight",
            op_df["Stock"]
        )

        msg = op_df.loc[op_df["Stock"] == selected_stock, "Message"].values[0]

        st.success(msg)
