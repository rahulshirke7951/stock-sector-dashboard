import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import os
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule

print("🚀 Starting the Smart Robot Chef...")

# ---------- Load Config ----------
with open("config.json") as f:
    config = json.load(f)

sectors = config["sectors"]
output_folder = config["output"]["folder"]
analytics = config["analytics"]
from_date = config.get("from_date")
to_date = config.get("to_date")

os.makedirs(output_folder, exist_ok=True)

# ---------- Helper Functions ----------
def auto_width(ws):
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2

def apply_heatmap(ws):
    # Rule: Red for negative, White for zero, Green for positive
    rule = ColorScaleRule(
        start_type="num", start_value=-15, start_color="F8696B",
        mid_type="num", mid_value=0, mid_color="FFFFFF",
        end_type="num", end_value=15, end_color="63BE7B"
    )
    # Apply to a large enough range
    ws.conditional_formatting.add("B2:Z100", rule)

def calculate_cagr(data):
    if data.empty: return 0
    days = (data.index[-1] - data.index[0]).days
    if days < 30: return 0 
    years = days / 365.25
    # Returns a Series of CAGR for all stocks
    return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1) * 100

# ---------- Process Each Sector ----------
for sector, stocks in sectors.items():
    try:
        print(f"📁 Processing Sector: {sector}")

        # FIXED: Removed {today} so it always overwrites 'SectorName.xlsx'
        filename = f"{output_folder}/{sector}.xlsx"

        # 1. Download Data (Cleaned)
        # auto_adjust=True handles stock splits/dividends automatically
        raw_data = yf.download(stocks, start=from_date, end=to_date, auto_adjust=True)

        if raw_data.empty:
            print(f"⚠️ No data found for {sector}, skipping...")
            continue

        # 2. Extract "Close" and flatten the names
        # If multiple stocks, yfinance gives a Multi-Index. We just want the ticker names.
        if isinstance(raw_data.columns, pd.MultiIndex):
            data = raw_data['Close']
        else:
            data = raw_data['Close'].to_frame(name=stocks[0])

        # 3. Fill missing blanks (The "Forward Fill" fix)
        data = data.ffill()

        # 4. Create the Excel file (Cooking)
        with pd.ExcelWriter(filename, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name="prices")

            if analytics.get("monthly_returns"):
                # 'ME' is the modern way to say Month End
                monthly_returns = data.resample("ME").last().pct_change() * 100
                monthly_returns.index = monthly_returns.index.strftime("%Y-%b")
                monthly_returns.to_excel(writer, sheet_name="monthly_returns")

            if analytics.get("yearly_summary"):
                summary = pd.DataFrame({
                    "Start Price": data.iloc[0],
                    "Latest Price": data.iloc[-1],
                    "Total Return %": ((data.iloc[-1] / data.iloc[0]) - 1) * 100
                })
                summary.to_excel(writer, sheet_name="summary")

            if analytics.get("cagr"):
                cagr_df = calculate_cagr(data).to_frame(name="CAGR %")
                cagr_df.to_excel(writer, sheet_name="cagr")

        # 5. Apply Formatting (The "Decorating" fix)
        wb = load_workbook(filename)
        for ws in wb.worksheets:
            auto_width(ws)
            # Only apply heatmap to sheets where math makes sense
            if ws.title in ["monthly_returns", "summary", "cagr"]:
                apply_heatmap(ws)
        wb.save(filename)

        print(f"✅ Successfully updated: {filename}")

    except Exception as e:
        print(f"🚨 Error in {sector}: {e}")

print("✨ All sectors updated!")
