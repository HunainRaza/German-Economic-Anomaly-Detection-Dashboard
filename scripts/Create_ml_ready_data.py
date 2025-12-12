"""
Filter Master Economic Data to ML-Ready Dataset
================================================
Extracts complete years (2015-2024) from master CSV

Usage:
    python scripts/create_ml_ready_data.py
"""

import pandas as pd
from pathlib import Path


def create_ml_ready_data(
    master_file='data/processed/master_economic_data.csv',
    output_file='data/processed/training_data_new.csv',
    start_year=2015,
    end_year=2024,
    min_completeness=0.6
):
    """
    Filter master data to ML-ready dataset
    
    Args:
        master_file: Path to master economic data CSV
        output_file: Path for output ML-ready CSV
        start_year: First year to include
        end_year: Last year to include
        min_completeness: Minimum % of non-null columns required (0-1)
    """
    
    print("=" * 70)
    print("CREATE ML-READY DATASET")
    print("=" * 70)
    
    # Read master data
    print(f"\n📄 Reading: {master_file}")
    df = pd.read_csv(master_file)
    print(f"   → {len(df)} years × {len(df.columns)} columns")
    print(f"   → Years: {df['Year'].min()}-{df['Year'].max()}")
    
    # Filter to year range
    print(f"\n🔍 Filtering years {start_year}-{end_year}...")
    filtered = df[(df['Year'] >= start_year) & (df['Year'] <= end_year)].copy()
    print(f"   → {len(filtered)} years remaining")
    
    # Calculate completeness for each row
    print(f"\n📊 Checking data completeness (min: {min_completeness*100}%)...")
    
    for idx, row in filtered.iterrows():
        non_null = row.notna().sum() - 1  # Exclude 'Year' column
        total_cols = len(filtered.columns) - 1
        completeness = non_null / total_cols
        
        status = "✓" if completeness >= min_completeness else "⚠️"
        print(f"   {status} {int(row['Year'])}: {completeness*100:.1f}% complete")
    
    # Filter to complete years only
    filtered['completeness'] = filtered.apply(
        lambda row: (row.notna().sum() - 1) / (len(filtered.columns) - 1),
        axis=1
    )
    
    complete = filtered[filtered['completeness'] >= min_completeness].copy()
    complete = complete.drop('completeness', axis=1)
    
    print(f"\n✅ {len(complete)} complete years selected")
    
    # Save
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"\n💾 Saving: {output_file}")
    complete.to_csv(output_file, index=False)
    
    size_kb = output_path.stat().st_size / 1024
    print(f"   → {len(complete)} years × {len(complete.columns)} columns")
    print(f"   → {size_kb:.1f} KB")
    
    print("\n" + "=" * 70)
    print("✅ SUCCESS!")
    print("=" * 70)
    print("\n💡 Next steps:")
    print(f"   python manage.py load_economic_data --file {output_file} --clear")
    print(f"   python manage.py train_models")
    print(f"   python manage.py detect_anomalies")
    
    return complete


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Create ML-ready dataset')
    parser.add_argument('--master', default='data/processed/master_economic_data.csv')
    parser.add_argument('--output', default='data/processed/training_data_new.csv')
    parser.add_argument('--start-year', type=int, default=2015)
    parser.add_argument('--end-year', type=int, default=2024)
    parser.add_argument('--min-completeness', type=float, default=0.6)
    
    args = parser.parse_args()
    
    create_ml_ready_data(
        master_file=args.master,
        output_file=args.output,
        start_year=args.start_year,
        end_year=args.end_year,
        min_completeness=args.min_completeness
    )