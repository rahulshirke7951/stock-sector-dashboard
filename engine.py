import json
import yfinance as yf
import pandas as pd
from datetime import datetime
import os

print("Loading config...")

with open("config.json") as f:
    config = json.load(f)

time_period = config["time_period"]
sectors = config["sectors"]
output_folder = config["output"]["folder"]

os.makedirs(output_folder, exist_ok=True)

today = datetime.utcnow().strftime("%Y-%m-%d")
filename = f"{output_folder}/dashboard_{today}.xlsx"

writer = pd.ExcelWriter(filename)

for sector, stocks in sectors.items():
    try:
        print(f"Processing {sector}")

        # Download data
        data = yf.download(stocks, period=time_period)["Close"]

        if data.empty:
            print(f"No data for {sector}")
            continue

        # 1️⃣ Yearly returns
        yearly_returns = (data.iloc[-1] / data.iloc[0] - 1) * 100
        yearly_returns = yearly_returns.to_frame(name="1Y Return %")

        # 2️⃣ Monthly returns calculation
        monthly_prices = data.resample("M").last()
        monthly_returns = monthly_prices.pct_change() * 100

        # Make month names nice
        monthly_returns.index = monthly_returns.index.strftime("%Y-%b")

        # Save to Excel
        data.to_excel(writer, sheet_name=f"{sector}_prices")
        yearly_returns.to_excel(writer, sheet_name=f"{sector}_yearly")
        monthly_returns.to_excel(writer, sheet_name=f"{sector}_monthly")

    except Exception as e:
        print(f"Error processing {sector}: {e}")

writer.close()

print("Dashboard created:", filename)
