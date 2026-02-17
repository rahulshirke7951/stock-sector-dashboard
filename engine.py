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

writer = pd.ExcelWriter(filename, engine="openpyxl")

for sector, stocks in sectors.items():
    print(f"Processing {sector}")
    data = yf.download(stocks, period=time_period)["Close"]

    returns = (data.iloc[-1] / data.iloc[0] - 1) * 100
    returns = returns.to_frame(name="Return %")

    data.to_excel(writer, sheet_name=f"{sector}_prices")
    returns.to_excel(writer, sheet_name=f"{sector}_returns")

writer.close()

print("Dashboard created:", filename)
