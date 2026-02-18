import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule

print("Loading config...")

with open("config.json") as f:
    config = json.load(f)

sectors = config["sectors"]
output_folder = config["output"]["folder"]
analytics = config["analytics"]

from_date = config.get("from_date")
to_date = config.get("to_date")

os.makedirs(output_folder, exist_ok=True)

today = datetime.utcnow().strftime("%Y-%m-%d")


# ---------- Auto column width ----------
def auto_width(ws):
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2


# ---------- Heatmap ----------
def apply_heatmap(ws):
    rule = ColorScaleRule(
        start_type="num", start_value=-20, start_color="F8696B",
        mid_type="num", mid_value=0, mid_color="FFFFFF",
        end_type="num", end_value=20, end_color="63BE7B"
    )
    ws.conditional_formatting.add("B2:Z500", rule)


# ---------- CAGR ----------
def calculate_cagr(data):
    days = (data.index[-1] - data.index[0]).days
    years = days / 365
    return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1) * 100


# ---------- Process Each Sector ----------
for sector, stocks in sectors.items():
    try:
        print(f"Processing {sector}")

        filename = f"{output_folder}/{sector}_{today}.xlsx"
        writer = pd.ExcelWriter(filename, engine="openpyxl")

        data = yf.download(stocks, start=from_date, end=to_date)["Close"]

        if data.empty:
            continue

        data.index = pd.to_datetime(data.index)

        # Prices
        data.to_excel(writer, sheet_name="prices")

        # Monthly Returns
        if analytics.get("monthly_returns"):
            monthly_prices = data.resample("ME").last()
            monthly_returns = monthly_prices.pct_change() * 100
            monthly_returns.index = monthly_returns.index.strftime("%Y-%b")
            monthly_returns.to_excel(writer, sheet_name="monthly_returns")

        # Yearly Summary
        if analytics.get("yearly_summary"):
            summary = pd.DataFrame({
                "Start Price": data.iloc[0],
                "Latest Price": data.iloc[-1]
            })
            summary["Total Return %"] = (
                (summary["Latest Price"] / summary["Start Price"] - 1) * 100
            )
            summary.to_excel(writer, sheet_name="summary")

        # CAGR
        if analytics.get("cagr"):
            cagr = calculate_cagr(data).to_frame(name="CAGR %")
            cagr.to_excel(writer, sheet_name="cagr")

        # Rolling 12M
        if analytics.get("rolling_12m"):
            rolling = data.pct_change(252) * 100
            rolling.to_excel(writer, sheet_name="rolling12m")

        # Sector Average
        if analytics.get("sector_average"):
            sector_avg = data.mean(axis=1).to_frame(name="Sector Avg Price")
            sector_avg.to_excel(writer, sheet_name="sector_average")

        writer.close()

        # Apply formatting
        wb = load_workbook(filename)
        for ws in wb.worksheets:
            auto_width(ws)
            if ws.title in ["monthly_returns", "rolling12m", "summary"]:
                apply_heatmap(ws)
        wb.save(filename)

        print(f"Created {filename}")

    except Exception as e:
        print(f"Error processing {sector}: {e}")
