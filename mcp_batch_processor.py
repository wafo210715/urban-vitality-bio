"""
MCP Batch Processor for Phase 1
Processes restaurants and saves analysis reports
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from pathlib import Path
from typing import List, Dict

PHOTO_DIR = Path("cache/restaurant_photos/photos")


def get_pending_restaurants() -> List[Dict]:
    """Get restaurants with photos but no analysis"""
    pending = []
    for farm_dir in sorted(PHOTO_DIR.glob("farm_*")):
        try:
            farm_id = int(farm_dir.name.replace("farm_", ""))
        except:
            continue

        for rest_dir in sorted(farm_dir.iterdir()):
            if not rest_dir.is_dir():
                continue

            analysis_path = rest_dir / "analysis_report.json"
            if analysis_path.exists():
                continue

            photos = sorted(rest_dir.glob("photo_*.jpg"))
            if not photos:
                continue

            # Get metadata
            info_path = rest_dir / "photo_info.json"
            if info_path.exists():
                with open(info_path, 'r', encoding='utf-8') as f:
                    info = json.load(f)
                lat = info.get('lat')
                lon = info.get('lon')
                place_id = info.get('place_id')
            else:
                lat = lon = place_id = None

            pending.append({
                'farm_id': farm_id,
                'name': rest_dir.name,
                'photos': [str(p) for p in photos],
                'lat': lat,
                'lon': lon,
                'place_id': place_id,
                'dir': str(rest_dir)
            })

    return pending


def save_analysis_report(restaurant: Dict, analyses: List[Dict], photo_files: List[str] = None):
    """Save analysis report for a restaurant with full schema matching existing reports"""
    rest_dir = Path(restaurant['dir'])

    # Aggregate results
    all_ingredients = set()
    all_cuisines = set()
    farmable = {'leafy_greens': set(), 'herbs': set(), 'aromatics': set(), 'vegetables': set()}
    recommendations = {
        'best_for_rooftop': set(),
        'best_for_podium': set(),
        'best_for_streetscape': set(),
        'quick_wins': set()
    }

    photo_analysis = []
    for i, analysis in enumerate(analyses):
        # Handle different response formats
        if isinstance(analysis, str):
            try:
                analysis = json.loads(analysis)
            except:
                analysis = {}
        if isinstance(analysis, list) and analysis:
            analysis = analysis[0]
        if not isinstance(analysis, dict):
            analysis = {}

        # Build photo analysis entry matching existing schema
        photo_entry = {
            'photo_index': i + 1,
            'is_food': analysis.get('is_food', False),
            'dish_name': analysis.get('dish_name'),
            'cuisine_type': analysis.get('cuisine_type'),
        }

        # Handle visible_ingredients - could be array of strings or objects
        visible_ingredients = analysis.get('visible_ingredients', [])
        if visible_ingredients:
            photo_entry['visible_ingredients'] = visible_ingredients
            # Extract ingredient names for aggregation
            for ing in visible_ingredients:
                if isinstance(ing, dict):
                    name = ing.get('name', '')
                    if name:
                        all_ingredients.add(name)
                elif isinstance(ing, str):
                    all_ingredients.add(ing)

        # Handle farmable_in_singapore - extract items from nested structure
        farmable_data = analysis.get('farmable_in_singapore', {})
        photo_entry['farmable_in_singapore'] = farmable_data

        for cat in ['leafy_greens', 'herbs', 'aromatics', 'vegetables']:
            cat_data = farmable_data.get(cat, {})
            if isinstance(cat_data, dict):
                items = cat_data.get('items', [])
            else:
                items = cat_data if isinstance(cat_data, list) else []
            if isinstance(items, list):
                farmable[cat].update(items)

        # Handle growing_recommendations
        recs_data = analysis.get('growing_recommendations', {})
        photo_entry['growing_recommendations'] = recs_data

        for rec_type in ['best_for_rooftop', 'best_for_podium', 'best_for_streetscape', 'quick_wins']:
            items = recs_data.get(rec_type, [])
            if isinstance(items, list):
                recommendations[rec_type].update(items)

        # Add optional fields if present
        if analysis.get('local_sourcing_potential'):
            photo_entry['local_sourcing_potential'] = analysis['local_sourcing_potential']
        if 'vegetarian_friendly' in analysis:
            photo_entry['vegetarian_friendly'] = analysis['vegetarian_friendly']
        if analysis.get('notes'):
            photo_entry['notes'] = analysis['notes']

        # Add photo file path
        if photo_files and i < len(photo_files):
            photo_entry['photo_file'] = photo_files[i]

        photo_analysis.append(photo_entry)

        if analysis.get('cuisine_type'):
            all_cuisines.add(analysis['cuisine_type'])

    # Build full report matching existing schema
    report = {
        'name': restaurant['name'],
        'lat': restaurant.get('lat'),
        'lon': restaurant.get('lon'),
        'place_id': restaurant.get('place_id'),
        'photos_analyzed': len([a for a in photo_analysis if a.get('is_food') or a.get('dish_name')]),
        'photo_analysis': photo_analysis,
        'photo_files': photo_files or [],
        'aggregated_ingredients': sorted(list(all_ingredients)),
        'cuisine_types': sorted(list(all_cuisines)),
        'errors': [],
        'image_dir': restaurant['dir'],
        'farmable_ingredients': {k: sorted(list(v)) for k, v in farmable.items()},
        'growing_recommendations': {k: sorted(list(v)) for k, v in recommendations.items()}
    }

    report_path = rest_dir / "analysis_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    pending = get_pending_restaurants()
    print(f"Total pending: {len(pending)}")

    # Group by farm
    by_farm = {}
    for r in pending:
        fid = r['farm_id']
        if fid not in by_farm:
            by_farm[fid] = []
        by_farm[fid].append(r)

    print(f"\nBy Farm:")
    for fid in sorted(by_farm.keys()):
        print(f"  Farm {fid}: {len(by_farm[fid])} restaurants")

    # Save pending list for Claude Code to process
    pending_path = PHOTO_DIR.parent / "pending_analysis.json"
    with open(pending_path, 'w', encoding='utf-8') as f:
        json.dump(pending, f, ensure_ascii=False, indent=2)
    print(f"\nPending list saved to: {pending_path}")

    # Show first restaurant details
    if pending:
        print(f"\nFirst restaurant:")
        print(f"  Name: {pending[0]['name']}")
        print(f"  Farm: {pending[0]['farm_id']}")
        print(f"  Photos: {len(pending[0]['photos'])}")
        print(f"  First photo: {pending[0]['photos'][0]}")


if __name__ == "__main__":
    main()
