import json
import yfinance as yf
import pandas as pd
import os
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule

# ---------- Setup ----------
with open("config.json") as f:
    config = json.load(f)

sectors = config["sectors"]
output_folder = config["output"]["folder"]
from_date = config.get("from_date", "2023-01-01")

os.makedirs(output_folder, exist_ok=True)

def auto_width(ws):
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

def apply_heatmap(ws):
    rule = ColorScaleRule(
        start_type="num", start_value=-15, start_color="F8696B", 
        mid_type="num", mid_value=0, mid_color="FFFFFF",         
        end_type="num", end_value=15, end_color="63BE7B"         
    )
    ws.conditional_formatting.add("B2:Z100", rule)

# ---------- Processing ----------
for sector, stocks in sectors.items():
    try:
        print(f"🔄 Processing {sector}...")
        # STATIC FILENAME for Overwrite Strategy
        filename = os.path.join(output_folder, f"{sector}.xlsx")

        # Download Data
        raw_data = yf.download(stocks, start=from_date, auto_adjust=True)
        data = raw_data['Close'] if 'Close' in raw_data.columns else raw_data
        data = data.ffill()

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name="prices")

            # 1. Monthly Returns (Newest to Oldest)
            monthly = data.resample("ME").last().pct_change() * 100
            monthly = monthly.sort_index(ascending=False)
            monthly.index = monthly.index.strftime("%Y-%b")
            monthly.to_excel(writer, sheet_name="monthly_returns")

            # 2. Quarterly Returns (Newest to Oldest)
            quarterly = data.resample("QE").last().pct_change() * 100
            quarterly = quarterly.sort_index(ascending=False)
            quarterly.index = quarterly.index.to_period("Q").astype(str)
            quarterly.to_excel(writer, sheet_name="quarterly_returns")

        # Apply Formatting
        wb = load_workbook(filename)
        for ws in wb.worksheets:
            auto_width(ws)
            if ws.title in ["monthly_returns", "quarterly_returns"]:
                apply_heatmap(ws)
        wb.save(filename)
        print(f"✅ Success: {filename}")

    except Exception as e:
        print(f"🚨 Error in {sector}: {e}")
