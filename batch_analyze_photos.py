"""
MCP Batch Analysis Script
- Find all photos without analysis
- Generate prompts for Claude Code to analyze via MCP
- Compile final report

Usage:
    python batch_analyze_photos.py  # List pending photos
    # Then use Claude Code MCP to analyze
    python batch_analyze_photos.py --compile  # Compile results
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from pathlib import Path
from typing import List, Dict
import geopandas as gpd
import pandas as pd


def get_pending_restaurants(photos_dir: str = "cache/restaurant_photos/photos") -> List[Dict]:
    """Get restaurants that have photos but no analysis"""
    photos_dir = Path(photos_dir)
    pending = []

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        try:
            farm_id = int(farm_dir.name.replace("farm_", ""))
        except ValueError:
            continue

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            restaurant_name = restaurant_dir.name
            analysis_path = restaurant_dir / "analysis_report.json"

            if not analysis_path.exists():
                photo_files = sorted(restaurant_dir.glob("photo_*.jpg"))
                if photo_files:  # Only include if has photos
                    pending.append({
                        'farm_id': farm_id,
                        'restaurant_name': restaurant_name,
                        'photo_count': len(photo_files),
                        'photo_files': [str(p) for p in photo_files],
                        'dir': str(restaurant_dir)
                    })

    return pending


def get_restaurants_without_photos(photos_dir: str = "cache/restaurant_photos/photos") -> List[Dict]:
    """Get restaurants that have directories but no photos yet"""
    photos_dir = Path(photos_dir)
    no_photos = []

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        try:
            farm_id = int(farm_dir.name.replace("farm_", ""))
        except ValueError:
            continue

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            photo_files = list(restaurant_dir.glob("photo_*.jpg"))
            if not photo_files:
                no_photos.append({
                    'farm_id': farm_id,
                    'restaurant_name': restaurant_dir.name,
                    'dir': str(restaurant_dir)
                })

    return no_photos


def get_analysis_progress(photos_dir: str = "cache/restaurant_photos/photos") -> Dict:
    """Get analysis progress statistics"""
    photos_dir = Path(photos_dir)
    stats = {
        'total_restaurants': 0,
        'analyzed': 0,
        'pending': 0,
        'total_photos': 0,
        'by_farm': {}
    }

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        farm_id = int(farm_dir.name.replace("farm_", ""))
        stats['by_farm'][farm_id] = {'analyzed': 0, 'pending': 0, 'photos': 0}

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            stats['total_restaurants'] += 1
            photo_files = list(restaurant_dir.glob("photo_*.jpg"))
            stats['total_photos'] += len(photo_files)
            stats['by_farm'][farm_id]['photos'] += len(photo_files)

            analysis_path = restaurant_dir / "analysis_report.json"
            if analysis_path.exists():
                stats['analyzed'] += 1
                stats['by_farm'][farm_id]['analyzed'] += 1
            else:
                stats['pending'] += 1
                stats['by_farm'][farm_id]['pending'] += 1

    return stats


def generate_mcp_batch(pending: List[Dict], batch_size: int = 10) -> List[str]:
    """Generate batch analysis prompts for Claude Code"""
    batches = []

    for i in range(0, len(pending), batch_size):
        batch = pending[i:i+batch_size]
        prompt = "Analyze these restaurant photos using MCP analyze_image tool:\n\n"

        for r in batch:
            prompt += f"## {r['restaurant_name']} (Farm {r['farm_id']})\n"
            prompt += f"Photos: {r['photo_count']}\n"
            for photo in r['photo_files'][:3]:  # Limit to 3 photos per restaurant for batch
                prompt += f"- {photo}\n"
            prompt += "\n"

        prompt += "\nFor each photo, use the MCP analyze_image tool with this prompt:\n"
        prompt += '''"Analyze this food photo for an urban farming project in Singapore. Return JSON:
{"is_food": bool, "dish_name": str, "cuisine_type": str, "visible_ingredients": [str], "farmable_in_singapore": {"leafy_greens": [], "herbs": [], "aromatics": [], "vegetables": []}, "growing_recommendations": {"best_for_rooftop": [], "best_for_podium": [], "best_for_streetscape": [], "quick_wins": []}}'''

        batches.append(prompt)

    return batches


def compile_analysis_report(restaurant_dir: str, analyses: List[Dict]) -> Dict:
    """Compile analysis results into a report format"""
    restaurant_dir = Path(restaurant_dir)

    # Load photo info
    photo_info_path = restaurant_dir / "photo_info.json"
    if photo_info_path.exists():
        with open(photo_info_path, 'r', encoding='utf-8') as f:
            photo_info = json.load(f)
    else:
        photo_info = {'name': restaurant_dir.name, 'lat': None, 'lon': None}

    # Aggregate ingredients
    all_ingredients = set()
    all_cuisines = set()
    farmable = {'leafy_greens': set(), 'herbs': set(), 'aromatics': set(), 'vegetables': set()}
    recommendations = {'best_for_rooftop': set(), 'best_for_podium': set(),
                       'best_for_streetscape': set(), 'quick_wins': set()}

    photo_analysis = []
    for i, analysis in enumerate(analyses):
        if isinstance(analysis, list):
            analysis = analysis[0] if analysis else {}

        photo_analysis.append({
            'photo_index': i + 1,
            **analysis
        })

        # Aggregate
        if analysis.get('cuisine_type'):
            all_cuisines.add(analysis['cuisine_type'])

        for cat in ['leafy_greens', 'herbs', 'aromatics', 'vegetables']:
            items = analysis.get('farmable_in_singapore', {}).get(cat, [])
            if isinstance(items, list):
                farmable[cat].update(items)

        for rec_type in ['best_for_rooftop', 'best_for_podium', 'best_for_streetscape', 'quick_wins']:
            items = analysis.get('growing_recommendations', {}).get(rec_type, [])
            if isinstance(items, list):
                recommendations[rec_type].update(items)

    report = {
        'name': photo_info.get('name', restaurant_dir.name),
        'lat': photo_info.get('lat'),
        'lon': photo_info.get('lon'),
        'place_id': photo_info.get('place_id'),
        'photos_analyzed': len(analyses),
        'photo_analysis': photo_analysis,
        'cuisine_types': list(all_cuisines),
        'farmable_ingredients': {k: sorted(list(v)) for k, v in farmable.items()},
        'growing_recommendations': {k: sorted(list(v)) for k, v in recommendations.items()},
        'image_dir': str(restaurant_dir)
    }

    # Save report
    report_path = restaurant_dir / "analysis_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report


def main():
    print("=" * 60)
    print("MCP BATCH ANALYSIS HELPER")
    print("=" * 60)

    # Get progress
    stats = get_analysis_progress()
    print(f"\nCurrent Status:")
    print(f"  Total restaurants (directories): {stats['total_restaurants']}")
    print(f"  Analyzed: {stats['analyzed']}")
    print(f"  Pending analysis: {stats['pending']}")
    print(f"  Total photos: {stats['total_photos']}")

    # Get pending (with photos)
    pending = get_pending_restaurants()
    no_photos = get_restaurants_without_photos()

    print(f"\nBreakdown:")
    print(f"  With photos, need analysis: {len(pending)}")
    print(f"  Without photos (need download): {len(no_photos)}")

    if pending:
        print(f"\n--- PENDING ANALYSIS (have photos) ---")
        by_farm = {}
        for r in pending:
            fid = r['farm_id']
            if fid not in by_farm:
                by_farm[fid] = []
            by_farm[fid].append(r)

        print(f"\nBy Farm:")
        for fid in sorted(by_farm.keys())[:10]:  # Show first 10 farms
            total_photos = sum(r['photo_count'] for r in by_farm[fid])
            print(f"  Farm {fid}: {len(by_farm[fid])} restaurants, {total_photos} photos")

        if len(by_farm) > 10:
            print(f"  ... and {len(by_farm) - 10} more farms")

        # Show first pending
        print(f"\nNext to analyze:")
        r = pending[0]
        print(f"  Name: {r['restaurant_name']}")
        print(f"  Farm: {r['farm_id']}")
        print(f"  Photos: {r['photo_count']}")

    if no_photos and '--verbose' in sys.argv:
        print(f"\n--- NEED PHOTO DOWNLOAD ---")
        by_farm = {}
        for r in no_photos:
            fid = r['farm_id']
            if fid not in by_farm:
                by_farm[fid] = []
            by_farm[fid].append(r)

        print(f"\nBy Farm:")
        for fid in sorted(by_farm.keys())[:10]:
            print(f"  Farm {fid}: {len(by_farm[fid])} restaurants")

        if len(by_farm) > 10:
            print(f"  ... and {len(by_farm) - 10} more farms")


if __name__ == "__main__":
    main()
