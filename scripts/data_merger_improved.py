"""
Economic Data Merger Script - Enhanced for DESTATIS Format
===========================================================
Intelligently merges DESTATIS economic indicator CSVs into a single master file.
Handles metadata, annotations, and the specific DESTATIS CSV structure.

Key improvements:
- Automatically skips metadata headers
- Cleans value annotations (e, ..., .)
- Handles empty columns from extra semicolons
- Preserves indicator names and units
- Creates clean, ML-ready datasets

Usage:
    # Initial merge of all files
    python data_merger_improved.py --create
    
    # Add new year data from a single file
    python data_merger_improved.py --update new_2025_data.csv
    
    # Show info about master file
    python data_merger_improved.py --info
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse
import sys
import re


class DESTATISDataMerger:
    """Merges and manages DESTATIS economic indicator data from CSV sources."""
    
    def __init__(self, data_dir='data/raw', output_dir='data/processed'):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Master file paths
        self.master_file = self.output_dir / 'master_economic_data.csv'
        self.ml_ready_file = self.output_dir / 'ml_ready_data.csv'
        
    def log(self, message, level='INFO'):
        """Print formatted log message."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {level}: {message}")
    
    def clean_value(self, value):
        """Clean a data value by removing annotations and converting to float.
        
        Handles:
        - 'e' annotations (estimates)
        - '...' (missing data)
        - '.' (not applicable)
        - Empty strings
        
        Returns:
            float or np.nan
        """
        if pd.isna(value):
            return np.nan
        
        value_str = str(value).strip()
        
        # Handle missing/not applicable indicators
        if value_str in ['...', '.', '', '-']:
            return np.nan
        
        # Remove 'e' annotation and any other letters
        cleaned = re.sub(r'[a-zA-Z]', '', value_str).strip()
        
        # Try to convert to float
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            return np.nan
    
    def read_destatis_csv(self, filepath):
        """Read a DESTATIS CSV file and extract indicator data.
        
        DESTATIS CSV structure:
        - Lines 1-4: Metadata (table ID, title, etc.)
        - Line 5: Year headers (with empty columns)
        - Lines 6+: Data rows (country, indicator, unit, values...)
        - Footer: Sources and copyright (starts with "__________")
        
        Returns:
            DataFrame with Year as index and indicators as columns
        """
        filepath = Path(filepath)
        if not filepath.exists():
            self.log(f"File not found: {filepath}", 'WARNING')
            return None
        
        try:
            # Read the entire file to find the data section
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                lines = f.readlines()
            
            # Find where actual data starts (after headers)
            data_start = None
            year_line_idx = None
            
            for idx, line in enumerate(lines):
                # Look for the year headers line (contains years like 2015, 2016, etc.)
                if re.search(r'20\d{2}', line):
                    year_line_idx = idx
                    data_start = idx + 1
                    break
            
            if year_line_idx is None or data_start is None:
                self.log(f"Could not find year headers...", 'ERROR')
                return None
            
            # Find where data ends (before footer)
            data_end = len(lines)
            for idx in range(data_start, len(lines)):
                if lines[idx].strip().startswith('__________') or lines[idx].strip().startswith('Source:'):
                    data_end = idx
                    break
            
            # Extract year headers
            year_line = lines[year_line_idx].strip().split(';')
            years = [col.strip() for col in year_line if col.strip() and re.match(r'^\d{4}$', col.strip())]
            
            if not years:
                self.log(f"No year columns found in {filepath.name}", 'ERROR')
                return None
            
            self.log(f"Found years: {years[0]} to {years[-1]}")
            
            # Parse data rows
            indicators_data = {}
            
            for idx in range(data_start, data_end):
                line = lines[idx].strip()
                if not line or line.startswith('__________'):
                    break
                
                parts = line.split(';')
                
                # Skip if line doesn't have enough parts
                if len(parts) < 4:
                    continue
                
                # Extract indicator information
                # Format: Country;Indicator Name;Unit;Value1;;Value2;;Value3;...
                country = parts[0].strip()
                indicator_name = parts[1].strip()
                unit = parts[2].strip()
                
                # Skip empty indicator names
                if not indicator_name:
                    continue
                
                # Create a unique column name
                if unit:
                    col_name = f"{indicator_name} ({unit})"
                else:
                    col_name = indicator_name
                
                # Extract values (they're in alternating positions due to empty columns)
                values = []
                value_positions = [i for i in range(3, len(parts), 2) if i < len(parts)]
                
                for pos in value_positions[:len(years)]:  # Only take as many values as we have years
                    if pos < len(parts):
                        cleaned_val = self.clean_value(parts[pos])
                        values.append(cleaned_val)
                    else:
                        values.append(np.nan)
                
                # Pad with NaN if we have fewer values than years
                while len(values) < len(years):
                    values.append(np.nan)
                
                # Store the indicator data
                indicators_data[col_name] = dict(zip(years, values))
            
            if not indicators_data:
                self.log(f"No indicators extracted from {filepath.name}", 'ERROR')
                return None
            
            # Create DataFrame
            df = pd.DataFrame(indicators_data)
            df.index.name = 'Year'
            df.index = df.index.astype(int)
            
            # Add prefix based on filename to avoid conflicts
            prefix = filepath.stem.replace('99911-', '').replace('_en', '')
            df.columns = [f"{prefix}_{col}" for col in df.columns]
            
            self.log(f"✓ Loaded {filepath.name}: {len(df)} years, {len(df.columns)} indicators")
            
            return df
            
        except Exception as e:
            self.log(f"Error reading {filepath.name}: {str(e)}", 'ERROR')
            import traceback
            traceback.print_exc()
            return None
    
    def create_master_file(self, force=False):
        """Create master file by merging all CSV files in data_dir."""
        
        if self.master_file.exists() and not force:
            self.log(f"Master file already exists: {self.master_file}", 'WARNING')
            response = input("Overwrite? (yes/no): ").lower()
            if response != 'yes':
                self.log("Operation cancelled", 'INFO')
                return False
        
        # Find all CSV files
        csv_files = sorted(self.data_dir.glob('99911-*.csv'))
        
        if not csv_files:
            self.log(f"No CSV files found in {self.data_dir}", 'ERROR')
            self.log(f"Looking for files matching pattern: 99911-*.csv", 'INFO')
            return False
        
        self.log("=" * 80)
        self.log(f"CREATING MASTER FILE FROM {len(csv_files)} CSV FILES")
        self.log("=" * 80)
        
        # Process each file
        dataframes = []
        for filepath in csv_files:
            self.log(f"\nProcessing: {filepath.name}")
            df = self.read_destatis_csv(filepath)
            
            if df is not None and not df.empty:
                dataframes.append(df)
                self.log(f"  Shape: {df.shape[0]} years × {df.shape[1]} indicators")
        
        if not dataframes:
            self.log("\n❌ No valid data extracted from any file", 'ERROR')
            return False
        
        # Merge all dataframes on Year index
        self.log("\n" + "=" * 80)
        self.log("MERGING DATAFRAMES")
        self.log("=" * 80)
        
        master_df = dataframes[0]
        self.log(f"Starting with: {master_df.shape}")
        
        for i, df in enumerate(dataframes[1:], 1):
            master_df = master_df.join(df, how='outer')
            self.log(f"After merging file {i+1}: {master_df.shape}")
        
        master_df = master_df.sort_index()
        
        # Create backup if file exists
        if self.master_file.exists():
            backup_file = self.output_dir / f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            self.master_file.rename(backup_file)
            self.log(f"\nBackup created: {backup_file.name}")
        
        # Save master file
        master_df.to_csv(self.master_file)
        
        self.log("\n" + "=" * 80)
        self.log("✅ MASTER FILE CREATED SUCCESSFULLY")
        self.log("=" * 80)
        self.log(f"Location: {self.master_file}")
        self.log(f"Shape: {master_df.shape[0]} years × {master_df.shape[1]} indicators")
        self.log(f"Year range: {master_df.index.min()} - {master_df.index.max()}")
        self.log(f"File size: {self.master_file.stat().st_size / 1024:.1f} KB")
        
        # Create ML-ready file (only complete rows)
        self.log("\n" + "=" * 80)
        self.log("CREATING ML-READY DATASET")
        self.log("=" * 80)
        
        # Find rows with at least 80% non-null values
        completeness_threshold = 0.8
        row_completeness = master_df.notna().sum(axis=1) / len(master_df.columns)
        ml_df = master_df[row_completeness >= completeness_threshold].copy()
        
        # Drop columns with more than 50% missing values
        col_completeness = ml_df.notna().sum(axis=0) / len(ml_df)
        ml_df = ml_df.loc[:, col_completeness >= 0.5]
        
        ml_df.to_csv(self.ml_ready_file)
        
        self.log(f"✅ ML-ready file created: {self.ml_ready_file.name}")
        self.log(f"Shape: {ml_df.shape[0]} years × {ml_df.shape[1]} indicators")
        self.log(f"Year range: {ml_df.index.min()} - {ml_df.index.max()}")
        self.log(f"Completeness: {(ml_df.notna().sum().sum() / ml_df.size * 100):.1f}% non-null values")
        
        return True
    
    def update_master_file(self, new_data_file):
        """Update master file with new year data from a CSV file."""
        
        if not self.master_file.exists():
            self.log("Master file doesn't exist. Run with --create first.", 'ERROR')
            return False
        
        new_data_path = Path(new_data_file)
        if not new_data_path.exists():
            self.log(f"New data file not found: {new_data_file}", 'ERROR')
            return False
        
        self.log("=" * 80)
        self.log(f"UPDATING MASTER FILE WITH: {new_data_file}")
        self.log("=" * 80)
        
        # Load existing master data
        master_df = pd.read_csv(self.master_file, index_col=0)
        master_df.index.name = 'Year'
        self.log(f"Current master: {len(master_df)} years ({master_df.index.min()}-{master_df.index.max()})")
        
        # Load new data using the DESTATIS reader
        new_df = self.read_destatis_csv(new_data_path)
        
        if new_df is None:
            return False
        
        self.log(f"New data: {len(new_df)} years")
        
        # Merge the dataframes
        updated_df = master_df.join(new_df, how='outer', rsuffix='_new')
        updated_df = updated_df.sort_index()
        
        # Create backup
        backup_file = self.output_dir / f"master_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.master_file.rename(backup_file)
        self.log(f"Backup created: {backup_file.name}")
        
        # Save updated master file
        updated_df.to_csv(self.master_file)
        
        self.log(f"\n✅ Master file updated")
        self.log(f"New shape: {updated_df.shape[0]} years × {updated_df.shape[1]} indicators")
        self.log(f"Year range: {updated_df.index.min()} - {updated_df.index.max()}")
        
        return True
    
    def show_info(self):
        """Display information about the current master file."""
        
        if not self.master_file.exists():
            self.log("Master file doesn't exist. Run with --create first.", 'WARNING')
            return
        
        master_df = pd.read_csv(self.master_file, index_col=0)
        
        self.log("=" * 80)
        self.log("MASTER FILE INFORMATION")
        self.log("=" * 80)
        self.log(f"Location: {self.master_file}")
        self.log(f"Size: {self.master_file.stat().st_size / 1024:.1f} KB")
        self.log(f"Last modified: {datetime.fromtimestamp(self.master_file.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.log(f"\nData shape: {master_df.shape[0]} years × {master_df.shape[1]} indicators")
        self.log(f"Year range: {master_df.index.min()} - {master_df.index.max()}")
        
        total_values = master_df.size
        missing_values = master_df.isnull().sum().sum()
        self.log(f"Missing values: {missing_values:,} ({missing_values/total_values*100:.1f}%)")
        
        # Analyze by category (prefix)
        self.log("\nIndicator categories:")
        categories = {}
        for col in master_df.columns:
            # Extract category from prefix (e.g., "0002_" from "0002_Labour force")
            cat = col.split('_')[0]
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in sorted(categories.items()):
            self.log(f"  {cat}: {count} indicators")
        
        # Show sample data
        self.log("\nSample data (first 5 years, first 5 indicators):")
        print(master_df.iloc[:5, :5].to_string())
        
        # Check if ML-ready file exists
        if self.ml_ready_file.exists():
            ml_df = pd.read_csv(self.ml_ready_file, index_col=0)
            self.log(f"\n📊 ML-ready file: {ml_df.shape[0]} years × {ml_df.shape[1]} indicators")


def main():
    """Main function to handle command-line usage."""
    
    parser = argparse.ArgumentParser(
        description='Merge DESTATIS economic indicator CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create master file from all CSV files in data/raw
  python data_merger_improved.py --create
  
  # Specify custom directories
  python data_merger_improved.py --create --data-dir /path/to/csvs --output-dir /path/to/output
  
  # Update with new year data
  python data_merger_improved.py --update data/raw/99911-0012_en.csv
  
  # Show information about current master file
  python data_merger_improved.py --info
  
  # Force recreate from scratch
  python data_merger_improved.py --create --force
        """
    )
    
    parser.add_argument('--create', action='store_true',
                       help='Create master file from all CSV files')
    parser.add_argument('--update', type=str, metavar='FILE',
                       help='Update master file with new data from FILE')
    parser.add_argument('--info', action='store_true',
                       help='Show information about current master file')
    parser.add_argument('--force', action='store_true',
                       help='Force recreate master file (with --create)')
    parser.add_argument('--data-dir', type=str, default='data/raw',
                       help='Directory containing CSV files (default: data/raw)')
    parser.add_argument('--output-dir', type=str, default='data/processed',
                       help='Output directory for master file (default: data/processed)')
    
    args = parser.parse_args()
    
    # Create merger instance
    merger = DESTATISDataMerger(data_dir=args.data_dir, output_dir=args.output_dir)
    
    # Handle commands
    if args.create:
        success = merger.create_master_file(force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.update:
        success = merger.update_master_file(args.update)
        sys.exit(0 if success else 1)
    
    elif args.info:
        merger.show_info()
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == '__main__':
    main()