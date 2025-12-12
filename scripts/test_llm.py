"""
Test LLM Integration
=====================
Quick test script to verify your LLM setup is working correctly.

Usage:
    python scripts/test_llm.py
    python scripts/test_llm.py --provider anthropic
    python scripts/test_llm.py --provider openai
    python scripts/test_llm.py --provider ollama
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.dev')
import django
django.setup()

from indicators.llm_service import AnomalyExplainer


def test_llm(provider: str = None):
    """
    Test LLM integration with sample anomaly data.
    """
    print("=" * 70)
    print("LLM INTEGRATION TEST")
    print("=" * 70)
    
    # Sample anomaly data (2020 COVID-19 impact)
    test_year = 2020
    test_indicators = {
        'gdp_growth_rate': -4.5,
        'inflation_rate': 0.5,
        'unemployment_rate': 4.2,
        'export_share_gdp': 43.4,
        'industrial_production_index': 95.3,
    }
    test_anomaly_score = -0.35
    
    historical_context = {
        'gdp_growth_rate': 1.2,
        'inflation_rate': 1.5,
        'unemployment_rate': 3.8,
        'export_share_gdp': 46.2,
        'industrial_production_index': 105.7,
    }
    
    print(f"\nTest Data:")
    print(f"  Year: {test_year}")
    print(f"  Anomaly Score: {test_anomaly_score}")
    print(f"\n  Indicators:")
    for key, value in test_indicators.items():
        avg = historical_context.get(key, 0)
        diff = value - avg
        print(f"    {key}: {value:.1f} (avg: {avg:.1f}, diff: {diff:+.1f})")
    
    # Determine provider
    if provider is None:
        provider = os.getenv('LLM_PROVIDER', 'anthropic')
    
    print(f"\nProvider: {provider.upper()}")
    
    # Test connection
    try:
        print("\n🔄 Initializing LLM explainer...")
        explainer = AnomalyExplainer(provider=provider)
        print("✅ LLM explainer initialized successfully")
        
        print("\n🤖 Generating explanation...")
        explanation = explainer.explain_anomaly(
            year=test_year,
            indicators=test_indicators,
            anomaly_score=test_anomaly_score,
            historical_context=historical_context
        )
        
        print("\n" + "=" * 70)
        print("✅ SUCCESS! LLM is working correctly.")
        print("=" * 70)
        
        print(f"\n📝 Generated Explanation for {test_year}:")
        print("-" * 70)
        print(explanation)
        print("-" * 70)
        
        # Show statistics
        word_count = len(explanation.split())
        char_count = len(explanation)
        print(f"\nStatistics:")
        print(f"  Words: {word_count}")
        print(f"  Characters: {char_count}")
        
        return True
        
    except ValueError as e:
        print(f"\n❌ Configuration Error: {e}")
        print("\n💡 Fix:")
        if "ANTHROPIC_API_KEY" in str(e):
            print("  1. Get API key from https://console.anthropic.com/")
            print("  2. Add to dev.env: ANTHROPIC_API_KEY=your-key-here")
        elif "OPENAI_API_KEY" in str(e):
            print("  1. Get API key from https://platform.openai.com/")
            print("  2. Add to dev.env: OPENAI_API_KEY=your-key-here")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print(f"\nError Type: {type(e).__name__}")
        
        if provider == "ollama":
            print("\n💡 Ollama troubleshooting:")
            print("  1. Install Ollama from https://ollama.com/")
            print("  2. Run: ollama pull llama3.2:3b")
            print("  3. Start server: ollama serve")
            print("  4. Test connection: curl http://localhost:11434/api/tags")
        
        return False


def show_config_status():
    """Show current LLM configuration status"""
    print("\n" + "=" * 70)
    print("CONFIGURATION STATUS")
    print("=" * 70)
    
    provider = os.getenv('LLM_PROVIDER', 'not set')
    print(f"\nLLM_PROVIDER: {provider}")
    
    # Check API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    print(f"\nAPI Keys:")
    print(f"  Anthropic: {'✅ Set' if anthropic_key else '❌ Not set'}")
    print(f"  OpenAI: {'✅ Set' if openai_key else '❌ Not set'}")
    print(f"  Ollama: ✅ No key needed (if installed)")
    
    # Check which provider is ready
    print(f"\nProvider Status:")
    if provider == 'anthropic':
        status = '✅ Ready' if anthropic_key else '❌ Missing API key'
        print(f"  Anthropic: {status}")
    elif provider == 'openai':
        status = '✅ Ready' if openai_key else '❌ Missing API key'
        print(f"  OpenAI: {status}")
    elif provider == 'ollama':
        print(f"  Ollama: ⚠️  Requires manual verification")
        print(f"           Run: curl http://localhost:11434/api/tags")
    else:
        print(f"  ⚠️  No valid provider configured")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test LLM integration')
    parser.add_argument(
        '--provider',
        type=str,
        choices=['anthropic', 'openai', 'ollama'],
        help='LLM provider to test'
    )
    parser.add_argument(
        '--config-only',
        action='store_true',
        help='Only show configuration status without testing'
    )
    
    args = parser.parse_args()
    
    if args.config_only:
        show_config_status()
    else:
        success = test_llm(provider=args.provider)
        
        if success:
            print("\n✅ Your LLM integration is working perfectly!")
            print("\n💡 Next steps:")
            print("  python manage.py detect_anomalies")
        else:
            print("\n❌ Please fix the errors above and try again.")
            sys.exit(1)