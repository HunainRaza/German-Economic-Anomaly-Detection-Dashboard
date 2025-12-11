"""
Django Management Command: Train ML Models with SARIMA

This replaces Prophet with SARIMA for forecasting.
SARIMA is more appropriate for annual economic data.

Usage: python manage.py train_models
"""

from django.core.management.base import BaseCommand
from indicators.models import EconomicIndicator, MLModel
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.statespace.sarimax import SARIMAX, SARIMAXResults
import pandas as pd
import numpy as np
import joblib
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')


class Command(BaseCommand):
    help = 'Train ML models on economic data (Isolation Forest + SARIMA)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--contamination',
            type=float,
            default=0.2,
            help='Expected proportion of anomalies (default: 0.2 = 20%)'
        )
        parser.add_argument(
            '--forecast-steps',
            type=int,
            default=3,
            help='Number of years to forecast ahead (default: 3)'
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("TRAINING ML MODELS (ISOLATION FOREST + SARIMA)")
        self.stdout.write("=" * 80)
        
        contamination = options['contamination']
        forecast_steps = options['forecast_steps']
        
        # Load data from database
        self.stdout.write("\n📊 Loading data from database...")
        df = pd.DataFrame(list(EconomicIndicator.objects.all().values()))
        
        if df.empty:
            self.stdout.write(self.style.ERROR("❌ No data found in database!"))
            self.stdout.write("Run: python manage.py load_economic_data first")
            return
        
        df = df.set_index('year')
        self.stdout.write(self.style.SUCCESS(f"   ✓ Loaded {len(df)} years of data ({df.index.min()}-{df.index.max()})"))
        
        # Create model directory
        model_dir = Path('data/models')
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # ====================================================================
        # 1. Train Isolation Forest for Anomaly Detection
        # ====================================================================
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("1️⃣ TRAINING ISOLATION FOREST FOR ANOMALY DETECTION")
        self.stdout.write("=" * 80)
        
        # Select features for anomaly detection
        # Only use features that exist in the data
        potential_features = [
            'gdp_growth_rate',
            'inflation_rate', 
            'unemployment_rate',
            'export_share_gdp',
            'industrial_production_index',
            'labour_force_participation',
            'youth_unemployment_rate'
        ]
        
        # Filter to only available columns that have non-null data
        features = [f for f in potential_features if f in df.columns and df[f].notna().sum() > 0]
        
        if len(features) < 3:
            self.stdout.write(self.style.ERROR(
                f"❌ Not enough features with data. Need at least 3, found: {features}"
            ))
            return
        
        self.stdout.write(f"\n📋 Using features: {', '.join(features)}")
        self.stdout.write(f"   (Excluded features with no data: {[f for f in potential_features if f not in features]})")
        
        # Filter to complete data only
        train_df = df[features].dropna()
        
        if len(train_df) < 5:
            self.stdout.write(self.style.WARNING(
                f"⚠️  Only {len(train_df)} complete records. Need at least 5 for reliable training."
            ))
            return
        
        self.stdout.write(f"\n📋 Features used: {', '.join(features)}")
        self.stdout.write(f"📊 Training samples: {len(train_df)}")
        self.stdout.write(f"🎯 Expected contamination: {contamination*100}%")
        
        # Standardize features (important for Isolation Forest)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(train_df)
        
        # Train Isolation Forest model
        iso_forest = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
            max_samples='auto',
            bootstrap=False
        )
        iso_forest.fit(X_scaled)
        
        # Calculate anomaly scores for validation
        anomaly_scores = iso_forest.score_samples(X_scaled)
        predictions = iso_forest.predict(X_scaled)
        n_anomalies = (predictions == -1).sum()
        
        self.stdout.write(f"\n📈 Training Results:")
        self.stdout.write(f"   • Anomalies detected: {n_anomalies}/{len(train_df)} ({n_anomalies/len(train_df)*100:.1f}%)")
        self.stdout.write(f"   • Anomaly score range: [{anomaly_scores.min():.3f}, {anomaly_scores.max():.3f}]")
        
        # Show which years are flagged as anomalies
        anomaly_years = train_df.index[predictions == -1].tolist()
        if anomaly_years:
            self.stdout.write(f"   • Anomalous years: {', '.join(map(str, anomaly_years))}")
        
        # Save model and scaler
        joblib.dump(iso_forest, model_dir / 'isolation_forest.pkl')
        joblib.dump(scaler, model_dir / 'scaler.pkl')
        
        self.stdout.write(self.style.SUCCESS("\n✅ Isolation Forest trained and saved"))
        self.stdout.write(f"   → {model_dir / 'isolation_forest.pkl'}")
        self.stdout.write(f"   → {model_dir / 'scaler.pkl'}")
        
        # Save model metadata to database
        MLModel.objects.update_or_create(
            model_type='ISOLATION_FOREST',
            version='1.0',
            defaults={
                'training_data_years': f"{train_df.index.min()}-{train_df.index.max()}",
                'model_file_path': str(model_dir / 'isolation_forest.pkl'),
                'notes': f'Trained on {len(train_df)} years. Contamination: {contamination}. Features: {len(features)}',
                'is_active': True
            }
        )
        
        # ====================================================================
        # 2. Train SARIMA for GDP Growth Forecasting
        # ====================================================================
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("2️⃣ TRAINING SARIMA FOR GDP GROWTH FORECASTING")
        self.stdout.write("=" * 80)
        
        gdp_series = df['gdp_growth_rate'].dropna()
        
        if len(gdp_series) < 5:
            self.stdout.write(self.style.WARNING("⚠️  Insufficient data for GDP forecasting"))
        else:
            self.stdout.write(f"\n📊 Training data: {len(gdp_series)} years ({gdp_series.index.min()}-{gdp_series.index.max()})")
            self.stdout.write(f"📈 GDP Growth range: [{gdp_series.min():.2f}%, {gdp_series.max():.2f}%]")
            
            # Auto-select best SARIMA order
            self.stdout.write("\n🔍 Finding optimal SARIMA parameters...")
            best_aic = np.inf
            best_order = None
            
            # Test different combinations
            for p in range(3):
                for d in range(2):
                    for q in range(3):
                        try:
                            model = SARIMAX(
                                gdp_series,
                                order=(p, d, q),
                                enforce_stationarity=False,
                                enforce_invertibility=False
                            )
                            results = model.fit(disp=False, maxiter=200)
                            
                            if results.aic < best_aic:
                                best_aic = results.aic
                                best_order = (p, d, q)
                                self.stdout.write(f"   → New best: SARIMA{(p,d,q)} - AIC: {results.aic:.2f}")
                        except:
                            continue
            
            if best_order is None:
                self.stdout.write(self.style.WARNING("⚠️  Could not find suitable SARIMA model"))
                best_order = (1, 1, 1)  # Fallback
                self.stdout.write(f"   Using fallback: SARIMA{best_order}")
            
            self.stdout.write(self.style.SUCCESS(f"\n🎯 Selected model: SARIMA{best_order}"))
            
            # Train final model
            model_gdp = SARIMAX(
                gdp_series,
                order=best_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            model_gdp_fit: SARIMAXResults = model_gdp.fit(disp=False, maxiter=200)
            
            # Calculate in-sample performance
            fitted_values = model_gdp_fit.fittedvalues
            residuals = model_gdp_fit.resid
            mape = np.mean(np.abs(residuals / gdp_series.loc[fitted_values.index])) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            self.stdout.write(f"\n📊 Model Performance (in-sample):")
            self.stdout.write(f"   • AIC: {model_gdp_fit.aic:.2f}")
            self.stdout.write(f"   • BIC: {model_gdp_fit.bic:.2f}")
            self.stdout.write(f"   • MAPE: {mape:.2f}%")
            self.stdout.write(f"   • RMSE: {rmse:.2f}")
            
            # Generate forecast
            forecast_result = model_gdp_fit.get_forecast(steps=forecast_steps)
            forecast = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)
            
            self.stdout.write(f"\n📈 Forecast for next {forecast_steps} years:")
            for year, value, lower, upper in zip(
                range(gdp_series.index.max() + 1, gdp_series.index.max() + forecast_steps + 1),
                forecast.values,
                conf_int.iloc[:, 0].values,
                conf_int.iloc[:, 1].values
            ):
                self.stdout.write(f"   • {year}: {value:.2f}% (95% CI: [{lower:.2f}%, {upper:.2f}%])")
            
            # Save model
            joblib.dump(model_gdp_fit, model_dir / 'sarima_gdp.pkl')
            joblib.dump(best_order, model_dir / 'sarima_gdp_order.pkl')
            
            self.stdout.write(self.style.SUCCESS("\n✅ SARIMA GDP model trained and saved"))
            self.stdout.write(f"   → {model_dir / 'sarima_gdp.pkl'}")
            
            # Save metadata
            MLModel.objects.update_or_create(
                model_type='SARIMA_GDP',
                version='1.0',
                defaults={
                    'training_data_years': f"{gdp_series.index.min()}-{gdp_series.index.max()}",
                    'model_file_path': str(model_dir / 'sarima_gdp.pkl'),
                    'notes': f'SARIMA{best_order}. AIC: {model_gdp_fit.aic:.2f}. MAPE: {mape:.2f}%',
                    'is_active': True
                }
            )
        
        # ====================================================================
        # 3. Train SARIMA for Inflation Forecasting
        # ====================================================================
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("3️⃣ TRAINING SARIMA FOR INFLATION FORECASTING")
        self.stdout.write("=" * 80)
        
        inf_series = df['inflation_rate'].dropna()
        
        if len(inf_series) < 5:
            self.stdout.write(self.style.WARNING("⚠️  Insufficient data for inflation forecasting"))
        else:
            self.stdout.write(f"\n📊 Training data: {len(inf_series)} years ({inf_series.index.min()}-{inf_series.index.max()})")
            self.stdout.write(f"📈 Inflation range: [{inf_series.min():.2f}%, {inf_series.max():.2f}%]")
            
            # Auto-select best SARIMA order
            self.stdout.write("\n🔍 Finding optimal SARIMA parameters...")
            best_aic = np.inf
            best_order = None
            
            for p in range(3):
                for d in range(2):
                    for q in range(3):
                        try:
                            model = SARIMAX(
                                inf_series,
                                order=(p, d, q),
                                enforce_stationarity=False,
                                enforce_invertibility=False
                            )
                            results = model.fit(disp=False, maxiter=200)
                            
                            if results.aic < best_aic:
                                best_aic = results.aic
                                best_order = (p, d, q)
                                self.stdout.write(f"   → New best: SARIMA{(p,d,q)} - AIC: {results.aic:.2f}")
                        except:
                            continue
            
            if best_order is None:
                best_order = (1, 1, 1)
                self.stdout.write(f"   Using fallback: SARIMA{best_order}")
            
            self.stdout.write(self.style.SUCCESS(f"\n🎯 Selected model: SARIMA{best_order}"))
            
            # Train final model
            model_inf = SARIMAX(
                inf_series,
                order=best_order,
                enforce_stationarity=False,
                enforce_invertibility=False
            )
            model_inf_fit: SARIMAXResults = model_inf.fit(disp=False, maxiter=200)
            
            # Calculate performance
            fitted_values = model_inf_fit.fittedvalues
            residuals = model_inf_fit.resid
            mape = np.mean(np.abs(residuals / inf_series.loc[fitted_values.index])) * 100
            rmse = np.sqrt(np.mean(residuals ** 2))
            
            self.stdout.write(f"\n📊 Model Performance (in-sample):")
            self.stdout.write(f"   • AIC: {model_inf_fit.aic:.2f}")
            self.stdout.write(f"   • BIC: {model_inf_fit.bic:.2f}")
            self.stdout.write(f"   • MAPE: {mape:.2f}%")
            self.stdout.write(f"   • RMSE: {rmse:.2f}")
            
            # Generate forecast
            forecast_result = model_inf_fit.get_forecast(steps=forecast_steps)
            forecast = forecast_result.predicted_mean
            conf_int = forecast_result.conf_int(alpha=0.05)
            
            self.stdout.write(f"\n📈 Forecast for next {forecast_steps} years:")
            for year, value, lower, upper in zip(
                range(inf_series.index.max() + 1, inf_series.index.max() + forecast_steps + 1),
                forecast.values,
                conf_int.iloc[:, 0].values,
                conf_int.iloc[:, 1].values
            ):
                self.stdout.write(f"   • {year}: {value:.2f}% (95% CI: [{lower:.2f}%, {upper:.2f}%])")
            
            # Save model
            joblib.dump(model_inf_fit, model_dir / 'sarima_inflation.pkl')
            joblib.dump(best_order, model_dir / 'sarima_inflation_order.pkl')
            
            self.stdout.write(self.style.SUCCESS("\n✅ SARIMA Inflation model trained and saved"))
            self.stdout.write(f"   → {model_dir / 'sarima_inflation.pkl'}")
            
            # Save metadata
            MLModel.objects.update_or_create(
                model_type='SARIMA_INFLATION',
                version='1.0',
                defaults={
                    'training_data_years': f"{inf_series.index.min()}-{inf_series.index.max()}",
                    'model_file_path': str(model_dir / 'sarima_inflation.pkl'),
                    'notes': f'SARIMA{best_order}. AIC: {model_inf_fit.aic:.2f}. MAPE: {mape:.2f}%',
                    'is_active': True
                }
            )
        
        # ====================================================================
        # Summary
        # ====================================================================
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ ALL MODELS TRAINED SUCCESSFULLY"))
        self.stdout.write("=" * 80)
        
        self.stdout.write("\n📁 Saved Models:")
        for pkl_file in model_dir.glob('*.pkl'):
            size = pkl_file.stat().st_size / 1024  # KB
            self.stdout.write(f"   • {pkl_file.name} ({size:.1f} KB)")
        
        self.stdout.write("\n💡 Next Steps:")
        self.stdout.write("   1. Run anomaly detection: python manage.py detect_anomalies")
        self.stdout.write("   2. Generate forecasts: python manage.py generate_forecasts")
        self.stdout.write("   3. Start dashboard: python dashboard/app.py")
        
        self.stdout.write("\n" + "=" * 80)