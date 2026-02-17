import pandas as pd

# Load your stock sector data
df = pd.read_csv('data.csv', parse_dates=['Date'], index_col='Date')

# Resample to monthly data (Month End)
df = df.resample('ME').mean()

# Continue with your processing...
print(df.head())
