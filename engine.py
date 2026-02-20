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
from_date = config.get("from_date")
to_date = config.get("to_date")

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

for sector, stocks in sectors.items():
    try:
        print(f"🔄 Processing {sector}...")
        filename = f"{output_folder}/{sector}.xlsx"

        raw_data = yf.download(stocks, start=from_date, end=to_date, auto_adjust=True)
        # Fix for yfinance structure
        if 'Close' in raw_data.columns:
            data = raw_data['Close']
        else:
            data = raw_data
            
        data = data.ffill()

        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name="prices")

            # Monthly Returns
            monthly = data.resample("ME").last().pct_change() * 100
            monthly = monthly.sort_index(ascending=False)
            monthly.index = monthly.index.strftime("%Y-%b")
            monthly.to_excel(writer, sheet_name="monthly_returns")

            # Quarterly Returns
            quarterly = data.resample("QE").last().pct_change() * 100
            quarterly = quarterly.sort_index(ascending=False)
            quarterly.index = quarterly.index.to_period("Q").astype(str)
            quarterly.to_excel(writer, sheet_name="quarterly_returns")

        # Formatting
        wb = load_workbook(filename)
        for ws in wb.worksheets:
            auto_width(ws)
            if ws.title in ["monthly_returns", "quarterly_returns"]:
                apply_heatmap(ws)
        wb.save(filename)

    except Exception as e:
        print(f"🚨 Error in {sector}: {e}")
