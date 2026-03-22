"""
MCP Photo Analysis Helper
Generate list of photos for MCP analysis and compile final report
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
from pathlib import Path
from typing import Dict, List
import geopandas as gpd
import pandas as pd


def get_all_photos(photos_dir: str = "cache/restaurant_photos/photos") -> List[Dict]:
    """
    Get all downloaded photos with metadata
    """
    photos_dir = Path(photos_dir)
    photos = []

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        farm_id = int(farm_dir.name.replace("farm_", ""))

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            restaurant_name = restaurant_dir.name

            # Check for existing analysis
            analysis_path = restaurant_dir / "analysis_report.json"
            has_analysis = analysis_path.exists()

            # Get all photos
            photo_files = sorted(restaurant_dir.glob("photo_*.jpg"))

            for photo_path in photo_files:
                photos.append({
                    'farm_id': farm_id,
                    'restaurant_name': restaurant_name,
                    'photo_path': str(photo_path),
                    'photo_name': photo_path.name,
                    'has_analysis': has_analysis
                })

    return photos


def get_photos_without_analysis(photos_dir: str = "cache/restaurant_photos/photos") -> List[Dict]:
    """Get photos that don't have analysis yet"""
    all_photos = get_all_photos(photos_dir)
    return [p for p in all_photos if not p['has_analysis']]


def get_restaurants_summary(photos_dir: str = "cache/restaurant_photos/photos") -> pd.DataFrame:
    """Get summary of all restaurants"""
    photos_dir = Path(photos_dir)
    restaurants = []

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        farm_id = int(farm_dir.name.replace("farm_", ""))

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            restaurant_name = restaurant_dir.name
            photo_files = list(restaurant_dir.glob("photo_*.jpg"))

            # Check for analysis
            analysis_path = restaurant_dir / "analysis_report.json"
            if analysis_path.exists():
                with open(analysis_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)
                has_analysis = True
                lat = analysis.get('lat')
                lon = analysis.get('lon')
            else:
                has_analysis = False
                lat = None
                lon = None

            restaurants.append({
                'farm_id': farm_id,
                'restaurant_name': restaurant_name,
                'photo_count': len(photo_files),
                'has_analysis': has_analysis,
                'lat': lat,
                'lon': lon
            })

    return pd.DataFrame(restaurants)


def compile_final_report(photos_dir: str = "cache/restaurant_photos/photos",
                        output_path: str = "farm_reports/mcp_analysis_report.json") -> Dict:
    """
    Compile final report from all MCP analysis results
    """
    photos_dir = Path(photos_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        'farms': {},
        'aggregated_ingredients': {
            'leafy_greens': set(),
            'herbs': set(),
            'aromatics': set(),
            'vegetables': set()
        },
        'growing_recommendations': {
            'best_for_rooftop': set(),
            'best_for_podium': set(),
            'best_for_streetscape': set(),
            'quick_wins': set()
        },
        'restaurants_with_analysis': 0,
        'restaurants_without_analysis': 0,
        'total_photos': 0
    }

    for farm_dir in sorted(photos_dir.glob("farm_*")):
        farm_id = int(farm_dir.name.replace("farm_", ""))
        farm_data = {
            'restaurants': [],
            'total_photos': 0
        }

        for restaurant_dir in sorted(farm_dir.iterdir()):
            if not restaurant_dir.is_dir():
                continue

            restaurant_name = restaurant_dir.name
            photo_files = list(restaurant_dir.glob("photo_*.jpg"))
            farm_data['total_photos'] += len(photo_files)
            report['total_photos'] += len(photo_files)

            # Check for analysis
            analysis_path = restaurant_dir / "analysis_report.json"
            if analysis_path.exists():
                with open(analysis_path, 'r', encoding='utf-8') as f:
                    analysis = json.load(f)

                restaurant_data = {
                    'name': restaurant_name,
                    'lat': analysis.get('lat'),
                    'lon': analysis.get('lon'),
                    'place_id': analysis.get('place_id'),
                    'photos_analyzed': analysis.get('photos_analyzed', 0),
                    'cuisine_types': analysis.get('cuisine_types', []),
                    'farmable_ingredients': analysis.get('farmable_ingredients', {}),
                    'growing_recommendations': analysis.get('growing_recommendations', {})
                }

                farm_data['restaurants'].append(restaurant_data)
                report['restaurants_with_analysis'] += 1

                # Aggregate ingredients
                for category in ['leafy_greens', 'herbs', 'aromatics', 'vegetables']:
                    items = analysis.get('farmable_ingredients', {}).get(category, [])
                    report['aggregated_ingredients'][category].update(items)

                # Aggregate recommendations
                for rec_type in ['best_for_rooftop', 'best_for_podium', 'best_for_streetscape', 'quick_wins']:
                    items = analysis.get('growing_recommendations', {}).get(rec_type, [])
                    report['growing_recommendations'][rec_type].update(items)
            else:
                report['restaurants_without_analysis'] += 1

        report['farms'][farm_id] = farm_data

    # Convert sets to lists for JSON serialization
    report['aggregated_ingredients'] = {
        k: sorted(list(v)) for k, v in report['aggregated_ingredients'].items()
    }
    report['growing_recommendations'] = {
        k: sorted(list(v)) for k, v in report['growing_recommendations'].items()
    }

    # Save report
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"Report saved to: {output_path}")
    return report


def link_to_poi(report_path: str = "farm_reports/mcp_analysis_report.json",
               food_poi_path: str = "json/food.geojson",
               output_path: str = "farm_reports/poi_linked_report.csv"):
    """
    Link analysis results back to original POI data
    """
    # Load report
    with open(report_path, 'r', encoding='utf-8') as f:
        report = json.load(f)

    # Load POI data
    food_poi = gpd.read_file(food_poi_path)

    # Create linked data
    linked = []
    for farm_id, farm_data in report['farms'].items():
        for restaurant in farm_data['restaurants']:
            # Find matching POI
            lat, lon = restaurant.get('lat'), restaurant.get('lon')
            if lat and lon:
                # Find nearest POI
                from shapely.geometry import Point
                point = Point(lon, lat)
                distances = food_poi.geometry.distance(point)
                nearest_idx = distances.idxmin()
                nearest_poi = food_poi.loc[nearest_idx]

                linked.append({
                    'farm_id': farm_id,
                    'restaurant_name': restaurant['name'],
                    'restaurant_lat': lat,
                    'restaurant_lon': lon,
                    'poi_name': nearest_poi.get('name'),
                    'poi_category': nearest_poi.get('category'),
                    'poi_subcategory': nearest_poi.get('subcategor'),
                    'poi_lat': nearest_poi.geometry.y,
                    'poi_lon': nearest_poi.geometry.x,
                    'distance_m': distances.min(),
                    'cuisine_types': ', '.join(restaurant.get('cuisine_types', [])),
                    'leafy_greens': ', '.join(restaurant.get('farmable_ingredients', {}).get('leafy_greens', [])),
                    'herbs': ', '.join(restaurant.get('farmable_ingredients', {}).get('herbs', [])),
                    'aromatics': ', '.join(restaurant.get('farmable_ingredients', {}).get('aromatics', [])),
                    'vegetables': ', '.join(restaurant.get('farmable_ingredients', {}).get('vegetables', []))
                })

    df = pd.DataFrame(linked)
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Linked report saved to: {output_path}")
    return df


def main():
    """Main function"""
    print("="*60)
    print("MCP ANALYSIS HELPER")
    print("="*60)

    # Get summary
    print("\n1. Restaurant Summary:")
    df = get_restaurants_summary()
    print(df.to_string())

    # Get photos without analysis
    print(f"\n2. Photos without analysis:")
    pending = get_photos_without_analysis()
    print(f"   Total pending: {len(pending)}")

    if pending:
        print(f"\n   First 10 photos to analyze:")
        for p in pending[:10]:
            print(f"   - {p['photo_path']}")

    # Compile report
    print("\n3. Compiling final report...")
    report = compile_final_report()
    print(f"   Restaurants with analysis: {report['restaurants_with_analysis']}")
    print(f"   Restaurants without analysis: {report['restaurants_without_analysis']}")
    print(f"   Total photos: {report['total_photos']}")

    # Link to POI
    print("\n4. Linking to POI data...")
    linked_df = link_to_poi()
    print(f"   Linked restaurants: {len(linked_df)}")


if __name__ == "__main__":
    main()
