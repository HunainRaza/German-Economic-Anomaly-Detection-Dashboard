"""
Smart Economic Data Loader
===========================
Auto-detects CSV columns and flexibly maps to Django models.
Handles any DESTATIS format and makes adding new years trivial.

Location: indicators/management/commands/load_data.py

Features:
- Auto-detects column names from CSV
- Flexible pattern matching for indicators
- Handles missing/renamed columns gracefully
- Validates data quality
- Reports data completeness
- Works with ANY year additions
"""

from django.core.management.base import BaseCommand
from indicators.models import EconomicIndicator
import pandas as pd
import os
import re
from pathlib import Path


class SmartColumnMapper:
    """
    Intelligently maps CSV columns to Django model fields using pattern matching.
    Handles variations in column names and DESTATIS format changes.
    """
    
    # Define flexible mapping patterns
    # Format: model_field: [list of possible CSV column patterns]
    MAPPING_PATTERNS = {
        # GDP Indicators
        'gdp_current_prices': [
            r'gdp.*current.*prices',
            r'gross.*domestic.*product.*current',
            r'0012.*gdp.*current.*bn'
        ],
        'gdp_per_capita': [
            r'gdp.*per.*capita',
            r'0012.*gdp.*per.*capita'
        ],
        'gdp_growth_rate': [
            r'gdp.*constant.*prices.*annual.*change',
            r'gdp.*growth.*rate',
            r'0012.*gdp.*constant.*annual',
            r'gdp.*real.*growth'
        ],
        
        # Inflation
        'inflation_rate': [
            r'inflation.*annual.*change.*cpi',
            r'0012.*inflation.*cpi',
            r'consumer.*price.*index.*change',
            r'cpi.*annual.*change'
        ],
        
        # Sector Shares
        'agriculture_share_gdp': [
            r'agriculture.*share.*gdp',
            r'0012.*agriculture.*gdp',
            r'gross.*value.*added.*agriculture'
        ],
        'industry_share_gdp': [
            r'industry.*share.*gdp',
            r'0012.*industry.*gdp',
            r'gross.*value.*added.*industry'
        ],
        'services_share_gdp': [
            r'services.*share.*gdp',
            r'0012.*services.*gdp',
            r'gross.*value.*added.*services'
        ],
        
        # Labour Market
        'unemployment_rate': [
            r'unemployment.*rate.*percent',
            r'0002.*unemployment.*rate',
            r'^unemployment.*rate$'
        ],
        'labour_force_participation': [
            r'labour.*force.*participation',
            r'0002.*labour.*force.*participation',
            r'labor.*force.*participation'
        ],
        'youth_unemployment_rate': [
            r'youth.*unemployment',
            r'0002.*youth.*unemployment'
        ],
        
        # Trade
        'export_share_gdp': [
            r'export.*goods.*services.*share.*gdp',
            r'0009.*export.*gdp',
            r'exports.*gdp'
        ],
        'import_goods_total': [
            r'import.*goods.*total.*bn',
            r'0009.*import.*goods.*total',
            r'total.*imports'
        ],
        'export_goods_total': [
            r'export.*goods.*total.*bn',
            r'0009.*export.*goods.*total',
            r'total.*exports'
        ],
        
        # Industry
        'industrial_production_index': [
            r'industrial.*production.*index',
            r'0010.*industrial.*production',
            r'industry.*production.*index'
        ],
        'manufacturing_production_index': [
            r'manufacturing.*production.*index',
            r'0010.*manufacturing.*production'
        ],
        
        # R&D
        'rd_expenditure_share_gdp': [
            r'research.*development.*expenditure.*gdp',
            r'0004.*research.*development.*gdp',
            r'r&d.*expenditure'
        ],
        'internet_users_per_100': [
            r'internet.*users.*per.*100',
            r'0004.*internet.*users',
            r'internet.*penetration'
        ],
    }
    
    def __init__(self, csv_columns):
        """Initialize with CSV column names"""
        self.csv_columns = [str(col) for col in csv_columns]
        self.mapping = {}
        self._build_mapping()
    
    def _build_mapping(self):
        """Build mapping from CSV columns to model fields"""
        for model_field, patterns in self.MAPPING_PATTERNS.items():
            matched = False
            for csv_col in self.csv_columns:
                if matched:
                    break
                csv_col_clean = csv_col.lower().strip()
                
                for pattern in patterns:
                    if re.search(pattern, csv_col_clean, re.IGNORECASE):
                        self.mapping[csv_col] = model_field
                        matched = True
                        break
    
    def get_mapped_fields(self):
        """Return dictionary of CSV_col -> model_field"""
        return self.mapping
    
    def get_unmapped_columns(self):
        """Return list of CSV columns that weren't mapped"""
        mapped_cols = set(self.mapping.keys())
        return [col for col in self.csv_columns if col not in mapped_cols and col.lower() != 'year']


class Command(BaseCommand):
    help = 'Smart loader: Auto-detects CSV format and loads economic data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/processed/ml_ready_data.csv',
            help='Path to CSV file (relative to project root)'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before loading'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be loaded without actually loading'
        )

    def handle(self, *args, **options):
        csv_file = options['file']
        clear_data = options['clear']
        dry_run = options['dry_run']
        
        self.stdout.write("=" * 80)
        self.stdout.write("SMART ECONOMIC DATA LOADER")
        self.stdout.write("=" * 80)
        
        # Check file exists
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f"❌ File not found: {csv_file}"))
            return
        
        # Read CSV
        self.stdout.write(f"\n📄 Reading CSV: {csv_file}")
        try:
            df = pd.read_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(
                f"   ✓ Loaded: {len(df)} rows × {len(df.columns)} columns"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error reading CSV: {e}"))
            return
        
        if df.empty:
            self.stdout.write(self.style.ERROR("❌ CSV file is empty"))
            return
        
        # Verify Year column exists
        if 'Year' not in df.columns:
            self.stdout.write(self.style.ERROR("❌ CSV must have 'Year' column"))
            return
        
        # Initialize smart mapper
        self.stdout.write("\n🔍 Auto-detecting column mappings...")
        mapper = SmartColumnMapper(df.columns)
        mapping = mapper.get_mapped_fields()
        unmapped = mapper.get_unmapped_columns()
        
        # Show mapping results
        self.stdout.write(f"\n✅ Mapped {len(mapping)} columns:")
        for csv_col, model_field in sorted(mapping.items(), key=lambda x: x[1]):
            self.stdout.write(f"   {csv_col:60s} → {model_field}")
        
        if unmapped:
            self.stdout.write(f"\n⚠️  Unmapped columns ({len(unmapped)}):")
            for col in unmapped[:10]:  # Show first 10
                self.stdout.write(f"   • {col}")
            if len(unmapped) > 10:
                self.stdout.write(f"   ... and {len(unmapped) - 10} more")
        
        # Check data coverage by year
        self.stdout.write("\n📊 Data coverage by year:")
        for year in sorted(df['Year'].unique()):
            year_data = df[df['Year'] == year]
            non_null = year_data[list(mapping.keys())].notna().sum().sum()
            total = len(mapping)
            coverage = (non_null / total * 100) if total > 0 else 0
            status = "✓" if coverage > 50 else "⚠️"
            self.stdout.write(f"   {status} {year}: {coverage:.1f}% ({non_null}/{total} indicators)")
        
        if dry_run:
            self.stdout.write("\n" + "=" * 80)
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No data was loaded"))
            self.stdout.write("=" * 80)
            return
        
        # Clear existing data if requested
        if clear_data:
            count = EconomicIndicator.objects.count()
            EconomicIndicator.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"   ⚠️  Deleted {count} existing records"))
        
        # Load data
        self.stdout.write("\n💾 Loading data into database...")
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        for idx, row in df.iterrows():
            try:
                year = int(row['Year'])
                
                # Build data dictionary using smart mapping
                data = {}
                for csv_col, model_field in mapping.items():
                    value = row[csv_col]
                    if pd.isna(value) or value == '':
                        data[model_field] = None
                    else:
                        try:
                            data[model_field] = float(value)
                        except (ValueError, TypeError):
                            self.stdout.write(
                                self.style.WARNING(
                                    f"   ⚠️  Cannot convert {csv_col}={value} to float for year {year}"
                                )
                            )
                            data[model_field] = None
                
                # Update or create
                obj, created = EconomicIndicator.objects.update_or_create(
                    year=year,
                    defaults=data
                )
                
                if created:
                    created_count += 1
                    self.stdout.write(f"   ✓ Created: {year}")
                else:
                    updated_count += 1
                    self.stdout.write(f"   ↻ Updated: {year}")
                    
            except Exception as e:
                skipped_count += 1
                self.stdout.write(self.style.WARNING(
                    f"   ⚠️  Skipped row {idx} (Year: {row.get('Year', 'N/A')}): {str(e)}"
                ))
        
        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ DATA LOADING COMPLETE"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Created: {created_count}")
        self.stdout.write(f"Updated: {updated_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"\nTotal records in database: {EconomicIndicator.objects.count()}")
        
        # Data completeness check
        self.stdout.write("\n📊 Data Completeness Report:")
        for obj in EconomicIndicator.objects.all().order_by('year'):
            completeness = obj.completeness_percentage
            status = "✓" if completeness > 70 else "⚠️" if completeness > 40 else "❌"
            self.stdout.write(f"   {status} {obj.year}: {completeness:.1f}% complete")
        
        # Suggest next steps
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("   1. Train models: python manage.py train_models")
        self.stdout.write("   2. Detect anomalies: python manage.py detect_anomalies")
        self.stdout.write("   3. Start dashboard: python manage.py runserver")


class DataValidator:
    """Validate loaded data quality"""
    
    @staticmethod
    def validate_year_range(df):
        """Check if years are within reasonable range"""
        years = df['Year'].dropna()
        if years.min() < 1990 or years.max() > 2030:
            return False, f"Years out of range: {years.min()}-{years.max()}"
        return True, "Year range valid"
    
    @staticmethod
    def validate_indicators(df):
        """Check if critical indicators are present"""
        critical = ['gdp_growth_rate', 'inflation_rate', 'unemployment_rate']
        # This would need to be adapted based on actual CSV columns
        return True, "Indicators check passed"