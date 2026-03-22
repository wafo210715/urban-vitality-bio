"""
Auto MCP Analyzer - Batch process restaurant photos
Generates analysis_report.json for each restaurant
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import re
from pathlib import Path
from typing import Dict, List, Any

PENDING_FILE = Path("cache/restaurant_photos/pending_analysis.json")
OUTPUT_DIR = Path("cache/restaurant_photos/analysis_reports")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_mcp_response(response: Any) -> Dict:
    """Parse MCP response and extract JSON"""
    if isinstance(response, dict):
        return response
    if isinstance(response, str):
        # Try to extract JSON from response
        try:
            # Try direct parse
            return json.loads(response)
        except:
            # Try to find JSON in text
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except:
                    pass
    return {}


def extract_farmable_items(analysis: Dict) -> Dict:
    """Extract farmable items from analysis"""
    farmable = {
        'leafy_greens': [],
        'herbs': [],
        'aromatics': [],
        'vegetables': []
    }

    farmable_data = analysis.get('farmable_in_singapore', {})

    for category in farmable.keys():
        items = farmable_data.get(category, {})
        if isinstance(items, dict):
            item_list = items.get('items', [])
            if isinstance(item_list, list):
                for item in item_list:
                    if isinstance(item, dict):
                        name = item.get('name', '')
                    else:
                        name = str(item)
                    if name:
                        farmable[category].append(name)
        elif isinstance(items, list):
            farmable[category] = [str(i) for i in items]

    return farmable


def extract_recommendations(analysis: Dict) -> Dict:
    """Extract growing recommendations"""
    recs = {
        'best_for_rooftop': [],
        'best_for_podium': [],
        'best_for_streetscape': [],
        'quick_wins': []
    }

    rec_data = analysis.get('growing_recommendations', {})

    for key in recs.keys():
        items = rec_data.get(key, [])
        if isinstance(items, list):
            recs[key] = [str(i) for i in items]

    return recs


def create_report(restaurant: Dict, analyses: List[Dict]) -> Dict:
    """Create analysis report for a restaurant"""
    all_farmable = {
        'leafy_greens': set(),
        'herbs': set(),
        'aromatics': set(),
        'vegetables': set()
    }
    all_recommendations = {
        'best_for_rooftop': set(),
        'best_for_podium': set(),
        'best_for_streetscape': set(),
        'quick_wins': set()
    }
    all_cuisines = set()
    photo_analyses = []

    for i, analysis in enumerate(analyses):
        if not analysis:
            continue

        is_food = analysis.get('is_food', True)
        if not is_food:
            photo_analyses.append({
                'photo_index': i + 1,
                'is_food': False,
                'note': 'Photo does not contain food'
            })
            continue

        photo_analyses.append({
            'photo_index': i + 1,
            'is_food': True,
            'dish_name': analysis.get('dish_name', 'Unknown'),
            'cuisine_type': analysis.get('cuisine_type', 'Unknown'),
            'visible_ingredients': analysis.get('visible_ingredients', [])
        })

        if analysis.get('cuisine_type'):
            all_cuisines.add(analysis.get('cuisine_type'))

        # Aggregate farmable items
        farmable = extract_farmable_items(analysis)
        for cat in all_farmable.keys():
            all_farmable[cat].update(farmable.get(cat, []))

        # Aggregate recommendations
        recs = extract_recommendations(analysis)
        for cat in all_recommendations.keys():
            all_recommendations[cat].update(recs.get(cat, []))

    report = {
        'name': restaurant['name'],
        'farm_id': restaurant['farm_id'],
        'lat': restaurant.get('lat'),
        'lon': restaurant.get('lon'),
        'place_id': restaurant.get('place_id'),
        'photos_analyzed': len(analyses),
        'photo_analysis': photo_analyses,
        'cuisine_types': list(all_cuisines),
        'farmable_ingredients': {k: sorted(list(v)) for k, v in all_farmable.items()},
        'growing_recommendations': {k: sorted(list(v)) for k, v in all_recommendations.items()},
        'image_dir': restaurant['dir']
    }

    return report


def save_report(restaurant: Dict, report: Dict):
    """Save report to restaurant directory"""
    rest_dir = Path(restaurant['dir'])
    report_path = rest_dir / "analysis_report.json"

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report_path


def get_pending_restaurants() -> List[Dict]:
    """Load pending restaurants"""
    if PENDING_FILE.exists():
        with open(PENDING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def main():
    pending = get_pending_restaurants()
    print(f"Total pending restaurants: {len(pending)}")

    # Group by farm
    by_farm = {}
    for r in pending:
        fid = r['farm_id']
        if fid not in by_farm:
            by_farm[fid] = []
        by_farm[fid].append(r)

    print(f"\nFarms to process: {len(by_farm)}")
    for fid in sorted(by_farm.keys()):
        print(f"  Farm {fid}: {len(by_farm[fid])} restaurants")


if __name__ == "__main__":
    main()
