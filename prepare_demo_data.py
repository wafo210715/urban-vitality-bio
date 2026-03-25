"""
Prepare demo data for interactive farm-to-restaurant visualization.

Aggregates Phase 1 farm data with restaurant photo analysis results,
filters restaurants by local sourcing potential, and outputs processed data.
"""

import json
import geopandas as gpd
from pathlib import Path
from collections import defaultdict

# Configuration
FARM_GEOJSON = 'farm_with_clusters/all_farm_phases.geojson'
FARM_REPORTS_DIR = Path('farm_reports')
RESTAURANT_ANALYSIS_DIR = Path('cache/restaurant_photos/photos')
OUTPUT_DIR = Path('demo')
OUTPUT_DIR.mkdir(exist_ok=True)

CRS_PROJECTED = 'EPSG:32648'
CRS_GEOGRAPHIC = 'EPSG:4326'


def load_farm_geometries():
    """Load farm geometries and filter to Phase 1."""
    print("Loading farm geometries...")
    farms = gpd.read_file(FARM_GEOJSON)
    farms = farms.to_crs(CRS_GEOGRAPHIC)

    # Filter Phase 1 farms
    phase1 = farms[farms['phase'] == 1].copy()
    print(f"Found {len(phase1)} Phase 1 farms")
    return phase1


def load_farm_report(farm_id):
    """Load a single farm report JSON."""
    report_path = FARM_REPORTS_DIR / f"farm_{farm_id}.json"
    if report_path.exists():
        with open(report_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None


def load_restaurant_analysis(farm_id, restaurant_name):
    """Load restaurant photo analysis if it exists."""
    # Try different path variations
    possible_paths = [
        RESTAURANT_ANALYSIS_DIR / f"farm_{farm_id}" / restaurant_name / "analysis_report.json",
    ]

    for path in possible_paths:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    return None


def find_restaurant_analysis(farm_id):
    """Find all restaurant analysis reports for a farm."""
    farm_dir = RESTAURANT_ANALYSIS_DIR / f"farm_{farm_id}"
    if not farm_dir.exists():
        return {}

    analyses = {}
    for restaurant_dir in farm_dir.iterdir():
        if restaurant_dir.is_dir():
            analysis_file = restaurant_dir / "analysis_report.json"
            if analysis_file.exists():
                try:
                    with open(analysis_file, 'r', encoding='utf-8') as f:
                        analyses[restaurant_dir.name] = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"Warning: Could not parse {analysis_file}: {e}")
    return analyses


def is_servable(analysis):
    """
    Determine if a restaurant is servable based on local sourcing potential.
    Returns (is_servable, can_provide, cannot_provide)
    """
    if not analysis:
        return False, [], []

    # Check local_sourcing_potential
    lsp = analysis.get('local_sourcing_potential', {})
    highly = lsp.get('highly_suitable', [])
    moderately = lsp.get('moderately_suitable', [])
    not_suitable = lsp.get('not_suitable', [])

    # If no local_sourcing_potential, check farmable_ingredients
    if not lsp:
        farmable = analysis.get('farmable_ingredients', {})
        all_farmable = []
        for items in farmable.values():
            if isinstance(items, list):
                all_farmable.extend(items)

        if all_farmable:
            return True, all_farmable, []
        return False, [], []

    can_provide = list(set(highly + moderately))

    # If nothing can be provided, it's not servable
    if not can_provide:
        return False, [], not_suitable

    return True, can_provide, not_suitable


def aggregate_farm_data(farm_gdf):
    """Aggregate all data for Phase 1 farms."""
    farms_data = []
    all_restaurants = {}  # Only servable restaurants (for backward compatibility)
    all_analyzed_restaurants = {}  # ALL analyzed restaurants (for GeoJSON export)
    crop_counter = defaultdict(int)
    total_analyzed = 0
    total_servable = 0

    for idx, row in farm_gdf.iterrows():
        # Try to get farm_id from various possible columns
        farm_id = row.get('FID')
        if farm_id is None or (isinstance(farm_id, float) and str(farm_id) == 'nan'):
            farm_id = row.get('Id')
        if farm_id is None or (isinstance(farm_id, float) and str(farm_id) == 'nan'):
            farm_id = idx
        farm_id = int(farm_id)

        # Get centroid in geographic coordinates
        centroid = row.geometry.centroid
        centroid_latlon = [centroid.y, centroid.x]

        # Load farm report
        report = load_farm_report(farm_id)

        # Get typology from geometry or report
        typology = row.get('typology', report.get('typology', 'unknown') if report else 'unknown')
        area_sqm = row.get('area_sqm', report.get('area_sqm', 0) if report else 0)
        cluster = row.get('cluster_label', report.get('cluster', 'unknown') if report else 'unknown')

        # Find restaurant analyses for this farm
        restaurant_analyses = find_restaurant_analysis(farm_id)

        servable_restaurants = []

        for rest_name, analysis in restaurant_analyses.items():
            total_analyzed += 1

            # First try to get coordinates from farm report (most reliable - from spatial analysis)
            # The photo analysis files sometimes have wrong coordinates due to secondary Google Places searches
            # finding different restaurant branches
            rest_lat = None
            rest_lon = None
            distance = None

            if report:
                rest_name_lower = rest_name.lower().strip()
                for poi in report.get('connected_pois', {}).get('food', []):
                    poi_name = poi.get('name', '').lower().strip()
                    # Skip empty/whitespace-only POI names
                    if not poi_name or len(poi_name) < 2:
                        continue
                    # Fuzzy match: exact match OR either name contains the other (min 4 chars for substring match)
                    # This handles cases like "Bells Crusine" vs "Bell's Cuisine" or "Din Tai Fung" vs "Din Tai Fung @ Suntec"
                    is_match = False
                    if poi_name == rest_name_lower:
                        is_match = True
                    elif len(rest_name_lower) >= 4 and rest_name_lower in poi_name:
                        is_match = True
                    elif len(poi_name) >= 4 and poi_name in rest_name_lower:
                        is_match = True

                    if is_match:
                        rest_lat = poi.get('lat')
                        rest_lon = poi.get('lon')
                        distance = poi.get('distance')
                        break

            # Fallback to photo analysis coordinates if not found in farm report
            if rest_lat is None:
                rest_lat = analysis.get('lat')
                rest_lon = analysis.get('lon')

            # Validate distance: calculate actual distance from farm centroid
            # Some upstream data has incorrect coordinates, so we verify here
            MAX_WALKING_DISTANCE = 500  # meters
            actual_distance = distance  # Use reported distance by default

            if rest_lat is not None and rest_lon is not None:
                # Calculate straight-line distance from farm centroid
                # Using rough conversion: 1 degree ≈ 111km
                lat_diff = abs(rest_lat - centroid_latlon[0])
                lon_diff = abs(rest_lon - centroid_latlon[1])
                straight_line_dist = (lat_diff**2 + lon_diff**2)**0.5 * 111000  # meters

                # If straight-line distance is much larger than reported distance,
                # the coordinates are likely wrong
                if straight_line_dist > MAX_WALKING_DISTANCE:
                    # Skip this restaurant - coordinates are wrong
                    continue
                elif distance is None or straight_line_dist > distance * 1.5:
                    # Use calculated distance if reported seems wrong
                    actual_distance = straight_line_dist

            # Check if servable
            servable, can_provide, cannot_provide = is_servable(analysis)

            # Get cuisine types
            cuisines = analysis.get('cuisine_types', [])

            # Get farmable ingredients
            farmable = analysis.get('farmable_ingredients', {})

            # Get growing recommendations
            growing = analysis.get('growing_recommendations', {})

            restaurant_data = {
                'name': rest_name,
                'lat': rest_lat,
                'lon': rest_lon,
                'distance': actual_distance,
                'cuisine_types': cuisines,
                'is_servable': servable,
                'can_provide': can_provide,
                'cannot_provide': cannot_provide,
                'farmable_ingredients': farmable,
                'growing_recommendations': growing
            }

            # Store in global restaurants dict (servable only, for backward compatibility)
            rest_key = f"{farm_id}_{rest_name}"
            all_restaurants[rest_key] = restaurant_data

            # Store ALL analyzed restaurants with farm association (for GeoJSON export)
            if rest_name not in all_analyzed_restaurants:
                all_analyzed_restaurants[rest_name] = {
                    'name': rest_name,
                    'lat': rest_lat,
                    'lon': rest_lon,
                    'farm_ids': [farm_id],
                    'distances': {str(farm_id): actual_distance},
                    'cuisine_types': cuisines,
                    'is_servable': servable,
                    'can_provide': can_provide,
                    'cannot_provide': cannot_provide,
                    'farmable_ingredients': farmable,
                    'growing_recommendations': growing
                }
            else:
                # Restaurant already exists, add this farm association
                all_analyzed_restaurants[rest_name]['farm_ids'].append(farm_id)
                all_analyzed_restaurants[rest_name]['distances'][str(farm_id)] = actual_distance

            if servable:
                total_servable += 1
                servable_restaurants.append(restaurant_data)

                # Count crops
                for crop in can_provide:
                    crop_counter[crop.lower().strip()] += 1

        # Aggregate recommended crops for this farm
        recommended_crops = {
            'leafy_greens': set(),
            'herbs': set(),
            'aromatics': set(),
            'vegetables': set()
        }

        for rest in servable_restaurants:
            farmable = rest.get('farmable_ingredients', {})
            for category, items in farmable.items():
                if category in recommended_crops and isinstance(items, list):
                    for item in items:
                        recommended_crops[category].add(item.strip() if item else '')

        # Convert sets to lists
        recommended_crops = {k: sorted(list(v)) for k, v in recommended_crops.items()}

        farm_data = {
            'farm_id': farm_id,
            'typology': typology,
            'cluster': cluster,
            'phase': 1,
            'centroid': centroid_latlon,
            'area_sqm': float(area_sqm) if area_sqm else 0,
            'servable_restaurants': servable_restaurants,
            'recommended_crops': recommended_crops,
            'total_restaurants_analyzed': len(restaurant_analyses),
            'total_servable': len(servable_restaurants)
        }

        farms_data.append(farm_data)

    # Calculate summary statistics
    summary = {
        'total_phase1_farms': len(farms_data),
        'farms_with_restaurants': sum(1 for f in farms_data if f['total_restaurants_analyzed'] > 0),
        'total_restaurants_analyzed': total_analyzed,
        'total_servable_restaurants': total_servable,
        'servable_percentage': round(total_servable / total_analyzed * 100, 1) if total_analyzed > 0 else 0,
        'most_common_crops': sorted(crop_counter.items(), key=lambda x: -x[1])[:20]
    }

    return {
        'farms': farms_data,
        'restaurants': all_restaurants,
        'all_analyzed_restaurants': all_analyzed_restaurants,
        'summary': summary
    }


def main():
    print("=" * 60)
    print("Farm Demo Data Preparation")
    print("=" * 60)

    # Load Phase 1 farm geometries
    phase1_farms = load_farm_geometries()

    # Aggregate all data
    print("\nAggregating farm and restaurant data...")
    demo_data = aggregate_farm_data(phase1_farms)

    # Save output
    output_path = OUTPUT_DIR / 'demo_data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(demo_data, f, indent=2, ensure_ascii=False)

    print(f"\nData saved to: {output_path}")

    # Print summary
    summary = demo_data['summary']
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Phase 1 Farms: {summary['total_phase1_farms']}")
    print(f"Farms with Restaurant Analysis: {summary['farms_with_restaurants']}")
    print(f"Total Restaurants Analyzed: {summary['total_restaurants_analyzed']}")
    print(f"Servable Restaurants: {summary['total_servable_restaurants']} ({summary['servable_percentage']}%)")
    print(f"\nTop 10 Most Common Crops:")
    for crop, count in summary['most_common_crops'][:10]:
        print(f"  - {crop}: {count} restaurants")


if __name__ == '__main__':
    main()
