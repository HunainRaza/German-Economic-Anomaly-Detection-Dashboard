"""
LLM-Powered Anomaly Explanation Service
========================================
Generates intelligent explanations for economic anomalies using LLMs.

Location: indicators/llm_service.py

Supports multiple LLM providers:
- Anthropic Claude (Haiku for cost efficiency)
- OpenAI (GPT-4o-mini for budget-friendly option)
- Ollama (free local models)
"""

import os
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class AnomalyExplainer:
    """
    Generate human-readable explanations for economic anomalies using LLMs.
    """
    
    def __init__(self, provider: str = "anthropic"):
        """
        Initialize the explainer with specified LLM provider.
        
        Args:
            provider: "anthropic", "openai", or "ollama"
        """
        self.provider = provider.lower()
        self._validate_config()
    
    def _validate_config(self):
        """Check if necessary API keys/configs are present"""
        if self.provider == "anthropic":
            if not os.getenv("ANTHROPIC_API_KEY"):
                raise ValueError("ANTHROPIC_API_KEY not found in environment")
        elif self.provider == "openai":
            if not os.getenv("OPENAI_API_KEY"):
                raise ValueError("OPENAI_API_KEY not found in environment")
        elif self.provider == "ollama":
            # Ollama runs locally, no API key needed
            pass
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")
    
    def explain_anomaly(
        self, 
        year: int, 
        indicators: Dict[str, float],
        anomaly_score: float,
        historical_context: Optional[Dict] = None
    ) -> str:
        """
        Generate explanation for why a year is anomalous.
        
        Args:
            year: The anomalous year
            indicators: Dict of indicator_name -> value
            anomaly_score: Anomaly score from Isolation Forest (-1 to 1)
            historical_context: Optional dict with historical averages
        
        Returns:
            Human-readable explanation string
        """
        
        prompt = self._build_prompt(year, indicators, anomaly_score, historical_context)
        
        try:
            if self.provider == "anthropic":
                return self._call_anthropic(prompt)
            elif self.provider == "openai":
                return self._call_openai(prompt)
            elif self.provider == "ollama":
                return self._call_ollama(prompt)
        except Exception as e:
            logger.error(f"LLM call failed for year {year}: {e}")
            return self._fallback_explanation(year, indicators)
    
    def _build_prompt(
        self, 
        year: int, 
        indicators: Dict[str, float],
        anomaly_score: float,
        historical_context: Optional[Dict] = None
    ) -> str:
        """Build the prompt for the LLM"""
        
        # Format indicators nicely
        indicators_text = "\n".join([
            f"  - {name.replace('_', ' ').title()}: {value:.2f}"
            for name, value in indicators.items()
        ])
        
        # Add historical context if available
        context_text = ""
        if historical_context:
            context_text = "\n\nHistorical Averages (for comparison):\n"
            context_text += "\n".join([
                f"  - {name.replace('_', ' ').title()}: {value:.2f}"
                for name, value in historical_context.items()
            ])
        
        prompt = f"""You are an economic analyst examining German economic data. 

A machine learning model (Isolation Forest) has flagged {year} as an economic anomaly with an anomaly score of {anomaly_score:.3f} (lower scores indicate stronger anomalies).

Economic Indicators for {year}:
{indicators_text}
{context_text}

Please provide a concise, professional explanation (2-3 sentences) of why {year} might be economically anomalous. Focus on:
1. Which specific indicators deviate significantly from normal patterns
2. Potential real-world economic events that could explain these deviations
3. The overall economic significance

Keep your response factual, focused, and under 150 words."""

        return prompt
    
    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic's Claude API"""
        try:
            import anthropic
            
            client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
            
            message = client.messages.create(
                model="claude-3-5-haiku-20241022",  # Most cost-effective model
                max_tokens=300,
                temperature=0.3,  # Lower temperature for more factual responses
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            return message.content[0].text.strip()
            
        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise
    
    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective model
                max_tokens=300,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "You are an economic analyst providing concise explanations of economic anomalies."},
                    {"role": "user", "content": prompt}
                ]
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise
    
    def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama instance with improved error handling"""
        try:
            import requests
            
            # Get model name from environment or use default
            model_name = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
            
            # First, check if model exists
            try:
                tags_response = requests.get("http://localhost:11434/api/tags", timeout=5)
                tags_response.raise_for_status()
                available_models = [model['name'] for model in tags_response.json().get('models', [])]
                
                if not available_models:
                    raise Exception("No models found in Ollama. Please pull a model first: ollama pull llama3.2:3b")
                
                # Check if requested model exists
                if model_name not in available_models:
                    # Use first available model as fallback
                    model_name = available_models[0]
                    logger.warning(f"Model {os.getenv('OLLAMA_MODEL', 'llama3.2:3b')} not found. Using {model_name} instead.")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to check Ollama models: {e}")
                # Continue anyway, let the generate call fail properly
            
            # Ollama API endpoint for generation
            url = "http://localhost:11434/api/generate"
            
            payload = {
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 300
                }
            }
            
            logger.info(f"Calling Ollama API with model: {model_name}")
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract response text
            if "response" in result:
                return result["response"].strip()
            else:
                raise Exception(f"Unexpected Ollama response format: {result}")
            
        except requests.exceptions.ConnectionError:
            raise Exception(
                "Cannot connect to Ollama. Make sure Ollama is running: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise Exception(
                "Ollama request timed out. The model might be too large or busy."
            )
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise
    
    def _fallback_explanation(self, year: int, indicators: Dict[str, float]) -> str:
        """
        Generate a simple rule-based explanation if LLM fails.
        This is the fallback to ensure the system always works.
        """
        explanations = []
        
        # Check GDP
        if 'gdp_growth_rate' in indicators:
            gdp = indicators['gdp_growth_rate']
            if gdp < -2:
                explanations.append(f"GDP contracted {abs(gdp):.1f}%")
            elif gdp > 4:
                explanations.append(f"Exceptional GDP growth {gdp:.1f}%")
        
        # Check inflation
        if 'inflation_rate' in indicators:
            inflation = indicators['inflation_rate']
            if inflation > 5:
                explanations.append(f"High inflation {inflation:.1f}%")
            elif inflation < 0:
                explanations.append(f"Deflation {abs(inflation):.1f}%")
        
        # Check unemployment
        if 'unemployment_rate' in indicators:
            unemployment = indicators['unemployment_rate']
            if unemployment > 8:
                explanations.append(f"High unemployment {unemployment:.1f}%")
            elif unemployment < 3:
                explanations.append(f"Exceptionally low unemployment {unemployment:.1f}%")
        
        if explanations:
            return f"{year} showed economic anomalies: " + "; ".join(explanations)
        else:
            return f"{year} showed multiple economic indicators deviating from normal patterns"


class BatchAnomalyExplainer:
    """
    Efficiently explain multiple anomalies with batch processing and caching.
    Useful for explaining all anomalies at once.
    """
    
    def __init__(self, provider: str = "anthropic"):
        self.explainer = AnomalyExplainer(provider=provider)
        self.cache = {}
    
    def explain_multiple(
        self,
        anomalies: list,
        historical_averages: Optional[Dict] = None,
        use_cache: bool = True
    ) -> Dict[int, str]:
        """
        Explain multiple anomalies efficiently.
        
        Args:
            anomalies: List of dicts with 'year', 'indicators', 'anomaly_score'
            historical_averages: Optional dict of indicator averages
            use_cache: Whether to use cached explanations
        
        Returns:
            Dict mapping year -> explanation
        """
        results = {}
        
        for anomaly in anomalies:
            year = anomaly['year']
            
            # Check cache
            if use_cache and year in self.cache:
                results[year] = self.cache[year]
                continue
            
            # Generate explanation
            explanation = self.explainer.explain_anomaly(
                year=year,
                indicators=anomaly['indicators'],
                anomaly_score=anomaly['anomaly_score'],
                historical_context=historical_averages
            )
            
            results[year] = explanation
            self.cache[year] = explanation
        
        return results


# Utility function for easy import
def get_explainer(provider: str = None) -> AnomalyExplainer:
    """
    Get an anomaly explainer instance.
    
    Args:
        provider: "anthropic", "openai", or "ollama". If None, uses env var.
    
    Returns:
        Configured AnomalyExplainer instance
    """
    if provider is None:
        provider = os.getenv("LLM_PROVIDER", "anthropic")
    
    return AnomalyExplainer(provider=provider)