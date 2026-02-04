from pathlib import Path
import os
import pandas as pd
from helper_functions import strip_accents, parse_date


def load_catalogue(csv_path: Path) -> pd.DataFrame:
    """Load the reference CSV into a *DataFrame* and build a normalised title column."""
    df = pd.read_csv(csv_path, dtype=str, encoding='utf-8').fillna("")
    if "Title" not in df.columns:
        raise ValueError("CSV must contain a 'title' column")
    df["_norm_title"] = df["Title"].apply(strip_accents)
    df["Date"] = df["Date"].apply(parse_date)
    df["Year"] = df['Date'].str.split('-').str[0]

    return df

def write_parquet_files(input_csv_folder, output_folder):
    """Convert CSV files to Parquet format."""
    if not input_csv_folder.exists():
        raise FileNotFoundError(f"Input folder not found: {input_csv_folder}")
    
    if not output_folder.exists():
        output_folder.mkdir(parents=True, exist_ok=True)
        print(f"Created output folder: {output_folder}")
    
    csv_files = [f for f in os.listdir(input_csv_folder) if f.endswith('.csv')]
    
    if not csv_files:
        print(f"No CSV files found in {input_csv_folder}")
        return
    
    print(f"Found {len(csv_files)} CSV file(s) to convert:\n")
    
    for file in csv_files:
        try:
            name = Path(file).stem
            print(f"  Processing: {name}...", end="")
            sys.stdout.flush()  # Ensure it's displayed
            
            csv_path = Path(input_csv_folder, file)
            df = load_catalogue(csv_path)
            
            output_path = Path(output_folder, name + ".parquet")
            df.to_parquet(output_path)
            
            print(f" ✓ Saved to {output_path.name}")
            sys.stdout.flush()
        except Exception as e:
            print(f" ✗ Error: {str(e)}")
            sys.stdout.flush()
            raise


def load_parquet_folder():
    """
    Load all Parquet files from a folder into a dictionary of DataFrames.
    Returns:
    --------
    dict : Dictionary with filenames (without extension) as keys and DataFrames as values
    """
    metadata_path = Path(Path(__file__).resolve().parent.parent.parent, "metadata", "parquet_files")
    datasets = {}
    
    for parquet_file in metadata_path.glob('*.parquet'):
        key = parquet_file.stem  # filename without .parquet extension
        datasets[key] = pd.read_parquet(parquet_file)
    
    return datasets

def csv_to_parquet():
    """Convert CSV files in metadata/csv_files to Parquet format in metadata/parquet_files."""
    try:
        # Get the metadata folder path (3 levels up from this file: tigertag -> src -> tigertag -> metadata)
        current_file = Path(__file__).resolve()
        metadata_folder = current_file.parent.parent.parent / "metadata"
        
        input_folder = metadata_folder / "csv_files"
        output_folder = metadata_folder / "parquet_files"
        
        print(f"Input folder: {input_folder}")
        print(f"Output folder: {output_folder}\n")
        
        # Validate paths
        if not metadata_folder.exists():
            raise FileNotFoundError(
                f"Metadata folder not found: {metadata_folder}\n"
                f"Expected location: {metadata_folder}\n"
                f"Current file location: {current_file}"
            )
        
        if not input_folder.exists():
            raise FileNotFoundError(
                f"CSV input folder not found: {input_folder}\n"
                f"Please create the folder and add CSV files to convert."
            )
        
        # Convert the files
        write_parquet_files(input_folder, output_folder)
        
    except Exception as e:
        error_msg = f"Error in csv_to_parquet: {str(e)}"
        print(error_msg)
        raise

# input_path = "C:/Users/seric/OneDrive/Documents/Princeton Tango Club/DJing/tango_metadata"
# output_path = "C:/Users/seric/OneDrive/Documents/GitHub/tigertag/metadata"
# write_parquet_files(input_path, output_path)