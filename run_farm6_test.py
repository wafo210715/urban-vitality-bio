"""
Test script for Farm 6 analysis with VLM
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import os

# Set environment variables before running:
# export GOOGLE_PLACES_API_KEY=your_key
# export ANTHROPIC_API_KEY=your_key
os.environ['ANTHROPIC_API_BASE'] = 'https://open.bigmodel.cn/api/anthropic'
os.environ['LLM_MODEL'] = 'glm-4.6v'

from farm_micro_analysis import FarmMicroAnalyzer

# Initialize with VLM
print("Initializing analyzer...")
analyzer = FarmMicroAnalyzer(use_vlm_api=True)

# Analyze farm 6
print("\nAnalyzing farm 6...")
report = analyzer.analyze_farm(6)

print(f"\nFarm 6 Analysis Complete:")
print(f"  Restaurants analyzed: {report['restaurants']['total_analyzed']}")
print(f"  Photos analyzed: {report['restaurants']['photos_analyzed']}")
print(f"  Ingredients found: {len(report['restaurants'].get('aggregated_ingredients', []))}")

# Show sample ingredients
if report['restaurants'].get('aggregated_ingredients'):
    print(f"  Sample ingredients: {report['restaurants']['aggregated_ingredients'][:10]}")
