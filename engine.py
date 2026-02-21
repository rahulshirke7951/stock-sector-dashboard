import json, yfinance as yf, pandas as pd, os
from openpyxl import load_workbook
from openpyxl.formatting.rule import ColorScaleRule

def main():
    # Load configuration dynamically
    with open("config.json") as f:
        config = json.load(f)
    
    sectors = config["sectors"]
    folder = config["output"]["folder"]
    
    # Logic: Always fetch data from 2022 to provide a 1-year buffer 
    # for 2023+ rolling calculations
    from_date = "2022-01-01" 
    os.makedirs(folder, exist_ok=True)

    for name, stocks in sectors.items():
        try:
            print(f"🔄 Processing: {name}")
            path = os.path.join(folder, f"{name}.xlsx")
            
            # Download based on the JSON stock list
            raw = yf.download(stocks, start=from_date, auto_adjust=True)
            
            # Handle both single-ticker and multi-ticker dataframes
            data = raw['Close'] if isinstance(raw.columns, pd.MultiIndex) else raw['Close'].to_frame(name=stocks[0])
            data = data.ffill()

            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                # Store prices for the dashboard's internal calculations
                data.to_excel(writer, sheet_name="prices")
                
                # Pre-calculate Returns for Heatmaps
                (data.resample("ME").last().pct_change() * 100).sort_index(ascending=False).to_excel(writer, sheet_name="monthly_returns")
                (data.resample("QE").last().pct_change() * 100).sort_index(ascending=False).to_excel(writer, sheet_name="quarterly_returns")
                
                # Pre-calculate 1-Year (252 day) Rolling Returns
                (data.pct_change(periods=252).dropna() * 100).to_excel(writer, sheet_name="rolling_12m")
            
            # Apply Excel conditional formatting for color scales
            wb = load_workbook(path)
            rule = ColorScaleRule(start_type="num", start_value=-15, start_color="F8696B", 
                                  mid_type="num", mid_value=0, mid_color="FFFFFF", 
                                  end_type="num", end_value=15, end_color="63BE7B")
            
            for s in ["monthly_returns", "quarterly_returns"]:
                if s in wb.sheetnames:
                    wb[s].conditional_formatting.add("B2:Z100", rule)
            wb.save(path)
            print(f"✅ Saved: {name}.xlsx")
            
        except Exception as e:
            print(f"🚨 Error in {name}: {e}")

if __name__ == "__main__":
    main()
