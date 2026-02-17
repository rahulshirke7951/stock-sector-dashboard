import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import os

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
filename = f"{output_folder}/dashboard_{today}.xlsx"

writer = pd.ExcelWriter(filename, engine="openpyxl")
sheet_written = False


# ---------- Excel Formatting Helper ----------
def format_sheet(ws):
    for col in ws.columns:
        max_length = max(len(str(cell.value)) if cell.value else 0 for cell in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 2


# ---------- CAGR ----------
def calculate_cagr(data):
    days = (data.index[-1] - data.index[0]).days
    years = days / 365
    return ((data.iloc[-1] / data.iloc[0]) ** (1 / years) - 1) * 100


for sector, stocks in sectors.items():
    try:
        print(f"Processing {sector}")

        # Download data
        data = yf.download(
            stocks,
            start=from_date,
            end=to_date,
            auto_adjust=False
        )["Close"]

        if data.empty:
            continue

        data.index = pd.to_datetime(data.index)

        # ---------- Prices ----------
        data.to_excel(writer, sheet_name=f"{sector}_prices")
        sheet_written = True

        # ---------- Monthly Returns ----------
        if analytics["monthly_returns"]:
            monthly_prices = data.resample("ME").last()
            monthly_returns = monthly_prices.pct_change() * 100
            monthly_returns.index = monthly_returns.index.strftime("%Y-%b")
            monthly_returns.to_excel(writer, sheet_name=f"{sector}_monthly")

        # ---------- Yearly Summary ----------
        if analytics["yearly_summary"]:
            summary = pd.DataFrame({
                "Start Price": data.iloc[0],
                "Latest Price": data.iloc[-1]
            })
            summary["Total Return %"] = (
                (summary["Latest Price"] / summary["Start Price"] - 1) * 100
            )
            summary.to_excel(writer, sheet_name=f"{sector}_summary")

        # ---------- CAGR ----------
        if analytics["cagr"]:
            cagr = calculate_cagr(data).to_frame(name="CAGR %")
            cagr.to_excel(writer, sheet_name=f"{sector}_cagr")

        # ---------- Rolling 12M ----------
        if analytics["rolling_12m"]:
            rolling = data.pct_change(252) * 100
            rolling.to_excel(writer, sheet_name=f"{sector}_rolling12m")

        # ---------- Sector Average ----------
        if analytics["sector_average"]:
            sector_avg = data.mean(axis=1)
            sector_avg = sector_avg.to_frame(name="Sector Average Price")
            sector_avg.to_excel(writer, sheet_name=f"{sector}_sector_avg")

        # ---------- Growth Since Start ----------
        if analytics["sector_growth_since_start"]:
            growth = (data.iloc[-1] / data.iloc[0] - 1) * 100
            growth = growth.to_frame(name="Growth Since Start %")
            growth.to_excel(writer, sheet_name=f"{sector}_growth")

    except Exception as e:
        print(f"Error processing {sector}: {e}")

# ensure file not empty
if not sheet_written:
    pd.DataFrame({"Message": ["No data available"]}).to_excel(writer, sheet_name="Info")

writer.close()

# Apply formatting
from openpyxl import load_workbook
wb = load_workbook(filename)

for ws in wb.worksheets:
    format_sheet(ws)

wb.save(filename)

print("Dashboard created:", filename)
