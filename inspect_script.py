import pandas as pd

# Load the .pkl file
df = pd.read_pickle(r"C:\Users\rapha.RAPHI\repositories\open-discourse\data\final\contributions_simplified.pkl")

# Display first few rows
print(df.head())

# Inspect structure
print(df.info())

# Check for missing values
print(df.isnull().sum())

# Show columns
print(df.columns)
