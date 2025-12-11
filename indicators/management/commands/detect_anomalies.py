"""
Django Management Command: Detect Anomalies
Uses trained Isolation Forest to detect anomalies in economic data
"""

from django.core.management.base import BaseCommand
from indicators.models import EconomicIndicator
import pandas as pd
import joblib
from pathlib import Path


class Command(BaseCommand):
    help = 'Detect anomalies in economic data using trained Isolation Forest model'

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("DETECTING ECONOMIC ANOMALIES")
        self.stdout.write("=" * 80)
        
        model_dir = Path('data/models')
        
        # Load models
        try:
            self.stdout.write("\n📦 Loading models...")
            iso_forest = joblib.load(model_dir / 'isolation_forest.pkl')
            scaler = joblib.load(model_dir / 'scaler.pkl')
            self.stdout.write(self.style.SUCCESS("   ✓ Models loaded"))
        except FileNotFoundError as e:
            self.stdout.write(self.style.ERROR(f"❌ Model files not found: {e}"))
            self.stdout.write("\n💡 Run this first: python manage.py train_models")
            return
        
        # Load data from database
        self.stdout.write("\n📊 Loading data from database...")
        df = pd.DataFrame(list(EconomicIndicator.objects.all().values()))
        
        if df.empty:
            self.stdout.write(self.style.ERROR("❌ No data in database!"))
            self.stdout.write("\n💡 Run this first: python manage.py load_economic_data")
            return
        
        df = df.set_index('year')
        self.stdout.write(self.style.SUCCESS(f"   ✓ Loaded {len(df)} years ({df.index.min()}-{df.index.max()})"))
        
        # Features used for anomaly detection (same as in training)
        potential_features = [
            'gdp_growth_rate',
            'inflation_rate',
            'unemployment_rate',
            'export_share_gdp',
            'industrial_production_index',
            'labour_force_participation',
            'youth_unemployment_rate'
        ]
        
        # Filter to available columns with actual data
        available_features = [f for f in potential_features if f in df.columns and df[f].notna().sum() > 0]
        if len(available_features) < 3:
            self.stdout.write(self.style.ERROR(f"❌ Not enough features available. Need at least 3, found: {available_features}"))
            return
        
        self.stdout.write(f"\n🔍 Using features: {', '.join(available_features)}")
        
        # Prepare data for prediction
        predict_df = df[available_features].dropna()
        
        if predict_df.empty:
            self.stdout.write(self.style.ERROR("❌ No complete records for prediction"))
            return
        
        self.stdout.write(f"   → {len(predict_df)} complete records")
        
        # Scale and predict
        X_scaled = scaler.transform(predict_df)
        predictions = iso_forest.predict(X_scaled)
        scores = iso_forest.score_samples(X_scaled)
        
        # Update database
        self.stdout.write("\n💾 Updating database with anomaly flags...")
        
        anomaly_count = 0
        for year, pred, score in zip(predict_df.index, predictions, scores):
            is_anomaly = (pred == -1)
            
            # Generate explanation
            if is_anomaly:
                anomaly_count += 1
                year_data = predict_df.loc[year]
                explanation_parts = []
                
                # Check which indicators are unusual
                if 'gdp_growth_rate' in year_data.index:
                    if year_data['gdp_growth_rate'] < -2:
                        explanation_parts.append(f"GDP contracted {year_data['gdp_growth_rate']:.1f}%")
                    elif year_data['gdp_growth_rate'] > 4:
                        explanation_parts.append(f"Exceptional GDP growth {year_data['gdp_growth_rate']:.1f}%")
                
                if 'inflation_rate' in year_data.index:
                    if year_data['inflation_rate'] > 5:
                        explanation_parts.append(f"High inflation {year_data['inflation_rate']:.1f}%")
                    elif year_data['inflation_rate'] < 0:
                        explanation_parts.append(f"Deflation {year_data['inflation_rate']:.1f}%")
                
                if 'unemployment_rate' in year_data.index:
                    if year_data['unemployment_rate'] > 8:
                        explanation_parts.append(f"High unemployment {year_data['unemployment_rate']:.1f}%")
                
                explanation = "; ".join(explanation_parts) if explanation_parts else "Multiple indicators deviate from normal patterns"
            else:
                explanation = None
            
            # Update record
            EconomicIndicator.objects.filter(year=year).update(
                is_anomaly=is_anomaly,
                anomaly_score=float(score),
                anomaly_explanation=explanation
            )
            
            status = "🔴 ANOMALY" if is_anomaly else "✓ Normal"
            self.stdout.write(f"   {status}: {year} (score: {score:.3f})")
        
        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ ANOMALY DETECTION COMPLETE"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Analyzed: {len(predict_df)} years")
        self.stdout.write(f"Anomalies detected: {anomaly_count}")
        
        if anomaly_count > 0:
            self.stdout.write(f"\n🔴 Anomalous years:")
            anomalies = EconomicIndicator.objects.filter(is_anomaly=True).order_by('year')
            for obj in anomalies:
                self.stdout.write(f"   • {obj.year}: {obj.anomaly_explanation}")