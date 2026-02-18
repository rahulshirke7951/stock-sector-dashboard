import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import PatternFill

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


# ---------- Excel Formatting ----------
def auto_width(ws):
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2


# ---------- Heatmap ----------
def apply_heatmap(ws):
    rule = ColorScaleRule(
        start_type="num", start_value=-20, start_color="F8696B",  # red
        mid_type="num", mid_value=0, mid_color="FFFFFF",          # white
        end_type="num", end_value=20, end_color="63BE7B"          # green
    )
    ws.conditional_formatting.add(f"B2:Z500", rule)


# ---------- CAGR ----------
def calculate_cagr(data):
    days = (data.index[-1] - data.index[0]).days
    years = days / 365
    return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1) * 100


# ---------- Process Each Sector ----------
for sector, stocks in sectors.items():
    try:
        print(f"Processing {sector}")

        # create separate file per sector
        filename = f"{output_folder}/{sector}_{today}.xlsx"
        writer = pd.ExcelWriter(filename, engine="openpyxl")

        data = yf.download(
            stocks,
            start=from_date,
            end=to_date
        )["Close"]

        if data.empty:
            continue

        data.index = pd.to_datetime(data.index)

        # ---------- Prices ----------
        data.to_excel(writer, sheet_name="prices")

        # ---------- Monthly Returns ----------
        if analytics["monthly_returns"]:
            monthly_prices = data.resample("ME").last()
            monthly_returns = monthly_prices.pct_change() * 100
            monthly_returns.index = monthly_returns.index.strftime("%Y-%b")
            monthly_returns.to_excel(writer, sheet_name="monthly_returns")

        # ---------- Yearly Summary ----------
        if analytics["yearly_summary"]:
            summary = pd.DataFrame({
                "Start Price": data.iloc[0],
                "Latest Price": data.iloc[-1]
            })
            summary["Total Return %"] = (
                (summary["Latest Price"] / summary["Start Price"] - 1) * 100
            )
            summary.to_excel(writer, sheet_name="summary")
