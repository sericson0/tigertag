from pathlib import Path
import os
import pandas as pd
from helper_functions import strip_accents, parse_date
input_path = "C:/Users/seric/OneDrive/Documents/Princeton Tango Club/DJing/tango_metadata"
output_path = "C:/Users/seric/OneDrive/Documents/GitHub/tigertag/metadata"

def load_catalogue(csv_path: Path) -> pd.DataFrame:
    """Load the reference CSV into a *DataFrame* and build a normalised title column."""
    df = pd.read_csv(csv_path, dtype=str, encoding='utf-8').fillna("")
    if "Title" not in df.columns:
        raise ValueError("CSV must contain a 'title' column")
    df["_norm_title"] = df["Title"].apply(strip_accents)
    df["Date"] = df["Date"].apply(parse_date)
    df["Year"] = df['Date'].str.split('-').str[0]

    return df


for file in os.listdir(input_path):
    name = Path(file).stem
    print(name)
    df = load_catalogue(Path(input_path, file))
    df.to_parquet(Path(output_path, name + ".parquet"))