"""Tests for metadata_handler module."""
import os
import sys
import tempfile
from pathlib import Path
import pytest
import pandas as pd

# Add parent directory to path so we can import the module
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from metadata_handler import (
    load_catalogue,
    write_parquet_files,
    load_parquet_folder,
    csv_to_parquet,
)


@pytest.fixture
def sample_csv_data():
    """Create sample CSV data for testing."""
    return pd.DataFrame({
        'Title': ['La Cumparsita', 'El Choclo', 'Adios Muchachos'],
        'Artist': ['Juan D\'Arienzo', 'Angel D\'Agostino', 'Carlos Gardel'],
        'Date': ['1937-03-15', '1941-07-22', '1930-12-01'],
        'Genre': ['Tango', 'Tango', 'Tango'],
    })


@pytest.fixture
def temp_metadata_dirs():
    """Create temporary directories for CSV input and Parquet output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_dir = Path(tmpdir) / 'csv_files'
        parquet_dir = Path(tmpdir) / 'parquet_files'
        csv_dir.mkdir()
        # Don't create parquet_dir - let write_parquet_files create it
        yield csv_dir, parquet_dir


class TestLoadCatalogue:
    """Tests for load_catalogue function."""
    
    def test_load_catalogue_success(self, sample_csv_data, temp_metadata_dirs):
        """Test loading a valid CSV file."""
        csv_dir, _ = temp_metadata_dirs
        csv_path = csv_dir / 'test_artist.csv'
        sample_csv_data.to_csv(csv_path, index=False)
        
        df = load_catalogue(csv_path)
        
        assert len(df) == 3
        assert 'Title' in df.columns
        assert '_norm_title' in df.columns
        assert 'Year' in df.columns
        assert df['Year'].iloc[0] == '1937'
    
    def test_load_catalogue_missing_title_column(self, temp_metadata_dirs):
        """Test that loading a CSV without Title column raises error."""
        csv_dir, _ = temp_metadata_dirs
        csv_path = csv_dir / 'invalid.csv'
        
        # Create CSV without Title column
        pd.DataFrame({'Artist': ['Test'], 'Date': ['2020-01-01']}).to_csv(csv_path, index=False)
        
        with pytest.raises(ValueError, match="CSV must contain a 'title' column"):
            load_catalogue(csv_path)


class TestWriteParquetFiles:
    """Tests for write_parquet_files function."""
    
    def test_write_parquet_files_success(self, sample_csv_data, temp_metadata_dirs):
        """Test successful conversion of CSV to Parquet."""
        csv_dir, parquet_dir = temp_metadata_dirs
        
        # Write sample CSV
        csv_path = csv_dir / 'Test Artist.csv'
        sample_csv_data.to_csv(csv_path, index=False)
        
        # Convert to parquet
        write_parquet_files(csv_dir, parquet_dir)
        
        # Verify parquet file was created
        parquet_path = parquet_dir / 'Test Artist.parquet'
        assert parquet_path.exists()
        
        # Verify content
        df = pd.read_parquet(parquet_path)
        assert len(df) == 3
        assert 'Title' in df.columns
        assert '_norm_title' in df.columns
    
    def test_write_parquet_files_creates_output_folder(self, sample_csv_data, temp_metadata_dirs):
        """Test that output folder is created if it doesn't exist."""
        csv_dir, parquet_dir = temp_metadata_dirs
        
        # Write sample CSV
        csv_path = csv_dir / 'Test.csv'
        sample_csv_data.to_csv(csv_path, index=False)
        
        # parquet_dir doesn't exist yet
        assert not parquet_dir.exists()
        
        # Convert to parquet
        write_parquet_files(csv_dir, parquet_dir)
        
        # Now it should exist
        assert parquet_dir.exists()
        assert (parquet_dir / 'Test.parquet').exists()
    
    def test_write_parquet_files_no_csv_files(self, temp_metadata_dirs, capsys):
        """Test behavior when no CSV files exist."""
        csv_dir, parquet_dir = temp_metadata_dirs
        parquet_dir.mkdir()
        
        write_parquet_files(csv_dir, parquet_dir)
        
        captured = capsys.readouterr()
        assert 'No CSV files found' in captured.out
    
    def test_write_parquet_files_missing_input_folder(self, temp_metadata_dirs):
        """Test that missing input folder raises error."""
        _, parquet_dir = temp_metadata_dirs
        nonexistent = Path(temp_metadata_dirs[0]).parent / 'nonexistent'
        
        with pytest.raises(FileNotFoundError, match="Input folder not found"):
            write_parquet_files(nonexistent, parquet_dir)
    
    def test_write_parquet_files_multiple_csv_files(self, sample_csv_data, temp_metadata_dirs):
        """Test converting multiple CSV files."""
        csv_dir, parquet_dir = temp_metadata_dirs
        
        # Write multiple CSVs
        for name in ['Artist A', 'Artist B', 'Artist C']:
            csv_path = csv_dir / f'{name}.csv'
            sample_csv_data.to_csv(csv_path, index=False)
        
        write_parquet_files(csv_dir, parquet_dir)
        
        # Verify all parquet files were created
        parquet_files = list(parquet_dir.glob('*.parquet'))
        assert len(parquet_files) == 3


class TestCsvToParquet:
    """Tests for csv_to_parquet function."""
    
    def test_csv_to_parquet_uses_correct_paths(self, monkeypatch, sample_csv_data):
        """Test that csv_to_parquet uses the correct metadata folder paths."""
        # This test verifies the function finds the correct paths
        # We'll just check that it doesn't error with the actual metadata folder
        # if it exists, or raises appropriate error if not
        
        # Get the expected metadata folder path
        metadata_handler_path = Path(__file__).resolve().parent.parent / 'metadata_handler.py'
        expected_metadata_folder = metadata_handler_path.parent.parent.parent / 'metadata'
        
        if expected_metadata_folder.exists():
            # If the folder exists, the function should work
            csv_to_parquet()  # Should not raise
        else:
            # If the folder doesn't exist, it should raise FileNotFoundError
            with pytest.raises(FileNotFoundError):
                csv_to_parquet()


class TestLoadParquetFolder:
    """Tests for load_parquet_folder function."""
    
    def test_load_parquet_folder_returns_dict(self):
        """Test that load_parquet_folder returns a dictionary."""
        result = load_parquet_folder()
        assert isinstance(result, dict)
    
    def test_load_parquet_folder_keys_are_filenames(self):
        """Test that dictionary keys are parquet filenames without extension."""
        result = load_parquet_folder()
        # Keys should be strings (artist names)
        for key in result.keys():
            assert isinstance(key, str)
            assert not key.endswith('.parquet')
    
    def test_load_parquet_folder_values_are_dataframes(self):
        """Test that dictionary values are DataFrames."""
        result = load_parquet_folder()
        for value in result.values():
            assert isinstance(value, pd.DataFrame)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
