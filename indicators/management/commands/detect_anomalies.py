"""
Django Management Command: Detect Anomalies with LLM Explanations
==================================================================
Uses trained Isolation Forest to detect anomalies and LLM to explain them.

Location: indicators/management/commands/detect_anomalies.py
"""

from django.core.management.base import BaseCommand
from indicators.models import EconomicIndicator
from indicators.llm_service import get_explainer
import pandas as pd
import joblib
from pathlib import Path
import os


class Command(BaseCommand):
    help = 'Detect anomalies in economic data and generate LLM-powered explanations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--llm-provider',
            type=str,
            choices=['anthropic', 'openai', 'ollama', 'none'],
            default=None,
            help='LLM provider to use for explanations (default: from env or anthropic)'
        )
        parser.add_argument(
            '--skip-llm',
            action='store_true',
            help='Use simple rule-based explanations instead of LLM'
        )

    def handle(self, *args, **options):
        self.stdout.write("=" * 80)
        self.stdout.write("DETECTING ECONOMIC ANOMALIES WITH LLM EXPLANATIONS")
        self.stdout.write("=" * 80)
        
        llm_provider = options.get('llm_provider')
        skip_llm = options.get('skip_llm')
        
        # Initialize LLM explainer if not skipped
        llm_explainer = None
        if not skip_llm:
            try:
                self.stdout.write("\n🤖 Initializing LLM explainer...")
                llm_explainer = get_explainer(provider=llm_provider)
                provider_name = llm_explainer.provider.upper()
                self.stdout.write(self.style.SUCCESS(f"   ✓ Using {provider_name} for explanations"))
            except Exception as e:
                self.stdout.write(self.style.WARNING(
                    f"   ⚠️  LLM initialization failed: {e}"
                ))
                self.stdout.write(self.style.WARNING(
                    "   → Falling back to rule-based explanations"
                ))
                skip_llm = True
        
        model_dir = Path('data/models')
        
        # Load models
        try:
            self.stdout.write("\n📦 Loading ML models...")
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
            self.stdout.write("\n💡 Run this first: python manage.py load_data")
            return
        
        df = df.set_index('year')
        self.stdout.write(self.style.SUCCESS(
            f"   ✓ Loaded {len(df)} years ({df.index.min()}-{df.index.max()})"
        ))
        
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
        available_features = [
            f for f in potential_features 
            if f in df.columns and df[f].notna().sum() > 0
        ]
        
        if len(available_features) < 3:
            self.stdout.write(self.style.ERROR(
                f"❌ Not enough features available. Need at least 3, found: {available_features}"
            ))
            return
        
        self.stdout.write(f"\n🔍 Using features: {', '.join(available_features)}")
        
        # Prepare data for prediction
        predict_df = df[available_features].dropna()
        
        if predict_df.empty:
            self.stdout.write(self.style.ERROR("❌ No complete records for prediction"))
            return
        
        self.stdout.write(f"   → {len(predict_df)} complete records")
        
        # Calculate historical averages for context
        historical_averages = predict_df.mean().to_dict()
        
        # Scale and predict
        X_scaled = scaler.transform(predict_df)
        predictions = iso_forest.predict(X_scaled)
        scores = iso_forest.score_samples(X_scaled)
        
        # Update database
        self.stdout.write("\n💾 Detecting anomalies and generating explanations...")
        
        anomaly_count = 0
        for year, pred, score in zip(predict_df.index, predictions, scores):
            is_anomaly = (pred == -1)
            
            # Generate explanation
            if is_anomaly:
                anomaly_count += 1
                year_data = predict_df.loc[year]
                indicators_dict = year_data.to_dict()
                
                if not skip_llm and llm_explainer:
                    # Use LLM for intelligent explanation
                    try:
                        explanation = llm_explainer.explain_anomaly(
                            year=int(year),
                            indicators=indicators_dict,
                            anomaly_score=float(score),
                            historical_context=historical_averages
                        )
                        self.stdout.write(self.style.SUCCESS(
                            f"   🤖 Generated LLM explanation for {year}"
                        ))
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(
                            f"   ⚠️  LLM failed for {year}: {e}"
                        ))
                        explanation = self._fallback_explanation(year, indicators_dict)
                else:
                    # Use rule-based explanation
                    explanation = self._fallback_explanation(year, indicators_dict)
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
        self.stdout.write(f"LLM explanations: {'Yes' if (not skip_llm and llm_explainer) else 'No (rule-based)'}")
        
        if anomaly_count > 0:
            self.stdout.write(f"\n🔴 Anomalous years with explanations:")
            anomalies = EconomicIndicator.objects.filter(is_anomaly=True).order_by('year')
            for obj in anomalies:
                self.stdout.write(f"\n   • {obj.year}:")
                # Word wrap the explanation for better readability
                explanation_lines = self._wrap_text(obj.anomaly_explanation, 70)
                for line in explanation_lines:
                    self.stdout.write(f"     {line}")
        
        # Cost estimation (if using paid APIs)
        if anomaly_count > 0 and not skip_llm and llm_explainer:
            self._show_cost_estimate(llm_explainer.provider, anomaly_count)
    
    def _fallback_explanation(self, year: int, indicators: dict) -> str:
        """
        Generate simple rule-based explanation as fallback.
        """
        explanation_parts = []
        
        # Check GDP
        if 'gdp_growth_rate' in indicators:
            gdp = indicators['gdp_growth_rate']
            if gdp < -2:
                explanation_parts.append(f"GDP contracted {abs(gdp):.1f}%")
            elif gdp > 4:
                explanation_parts.append(f"Exceptional GDP growth {gdp:.1f}%")
        
        # Check inflation
        if 'inflation_rate' in indicators:
            inflation = indicators['inflation_rate']
            if inflation > 5:
                explanation_parts.append(f"High inflation {inflation:.1f}%")
            elif inflation < 0:
                explanation_parts.append(f"Deflation {abs(inflation):.1f}%")
        
        # Check unemployment
        if 'unemployment_rate' in indicators:
            unemployment = indicators['unemployment_rate']
            if unemployment > 8:
                explanation_parts.append(f"High unemployment {unemployment:.1f}%")
            elif unemployment < 3:
                explanation_parts.append(f"Exceptionally low unemployment {unemployment:.1f}%")
        
        if explanation_parts:
            return "; ".join(explanation_parts)
        else:
            return "Multiple economic indicators deviate from normal patterns"
    
    def _wrap_text(self, text: str, width: int) -> list:
        """Simple text wrapping for console output"""
        if not text:
            return ["(No explanation)"]
        
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 <= width:
                current_line.append(word)
                current_length += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
        
        if current_line:
            lines.append(" ".join(current_line))
        
        return lines if lines else [text]
    
    def _show_cost_estimate(self, provider: str, anomaly_count: int):
        """Show estimated API costs"""
        self.stdout.write("\n💰 Estimated API Costs:")
        
        if provider == "anthropic":
            # Haiku: ~$0.25 per million input tokens, ~$1.25 per million output tokens
            # Estimate ~500 input tokens and ~200 output tokens per request
            input_tokens = anomaly_count * 500
            output_tokens = anomaly_count * 200
            cost = (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 1.25)
            self.stdout.write(f"   Claude Haiku: ~${cost:.4f} ({anomaly_count} requests)")
        
        elif provider == "openai":
            # GPT-4o-mini: ~$0.15 per million input tokens, ~$0.60 per million output tokens
            input_tokens = anomaly_count * 500
            output_tokens = anomaly_count * 200
            cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
            self.stdout.write(f"   GPT-4o-mini: ~${cost:.4f} ({anomaly_count} requests)")
        
        elif provider == "ollama":
            self.stdout.write(f"   Ollama (local): $0.00 (FREE!)")
        
        self.stdout.write("   Note: These are rough estimates. Actual costs may vary.")