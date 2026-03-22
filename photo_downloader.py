"""
Photo Downloader - Only download photos from Google Places API
No VLM analysis - photos will be analyzed separately via MCP
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import time
import requests
from typing import Optional, Dict, List
from pathlib import Path
import hashlib
import geopandas as gpd
import pandas as pd
from pyproj import CRS


# Google Places API Pricing (March 2025)
PRICING = {
    'nearby_search': 0.032,    # $0.032 per call
    'place_details': 0.017,    # $0.017 per call
    'place_photo': 0.007,      # $0.007 per call
}

CRS_GEOGRAPHIC = CRS.from_epsg(4326)


class PhotoDownloader:
    """Download restaurant photos from Google Places API"""

    def __init__(self,
                 google_api_key: Optional[str] = None,
                 cache_dir: str = "cache/restaurant_photos",
                 budget_limit: float = 385.0):
        """
        Initialize downloader

        Args:
            google_api_key: Google Places API Key
            cache_dir: Cache directory
            budget_limit: Budget limit in USD
        """
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir = self.cache_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)

        self.budget_limit = budget_limit
        self.total_cost = 0.0
        self.api_calls = 0
        self.photos_downloaded = 0
        self.restaurants_processed = 0

    def _check_budget(self) -> bool:
        """Check if budget exceeded"""
        if self.total_cost >= self.budget_limit:
            print(f"\n{'='*60}")
            print(f"BUDGET LIMIT REACHED: ${self.total_cost:.2f} / ${self.budget_limit:.2f}")
            print(f"{'='*60}\n")
            return False
        return True

    def _add_cost(self, api_type: str):
        """Add API call cost"""
        cost = PRICING.get(api_type, 0)
        self.total_cost += cost

    def _get_cache_path(self, prefix: str, key: str) -> Path:
        """Generate cache file path"""
        cache_key = hashlib.md5(f"{prefix}_{key}".encode()).hexdigest()
        return self.cache_dir / f"{prefix}_{cache_key}.json"

    def _load_cache(self, cache_path: Path) -> Optional[Dict]:
        """Load from cache"""
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_path: Path, data: Dict):
        """Save to cache"""
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def find_place_by_location(self, name: str, lat: float, lon: float, radius: int = 200) -> Optional[str]:
        """Find Place ID by name and location"""
        if not self._check_budget():
            return None

        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        params = {
            'key': self.google_api_key,
            'location': f"{lat},{lon}",
            'radius': radius,
            'name': name,
            'type': 'restaurant'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('status') == 'OK' and data.get('results'):
                self._add_cost('nearby_search')
                for result in data['results']:
                    if name.lower() in result.get('name', '').lower():
                        return result.get('place_id')
                return data['results'][0].get('place_id')
            elif data.get('status') == 'OVER_QUERY_LIMIT':
                print("\nRATE LIMIT - waiting 5 hours...")
                time.sleep(5 * 60 * 60)
                return self.find_place_by_location(name, lat, lon, radius)

        except Exception as e:
            print(f"Search error: {e}")

        return None

    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """Get place details with photos"""
        if not self._check_budget():
            return None

        cache_path = self._get_cache_path("details", place_id)
        cached = self._load_cache(cache_path)
        if cached:
            return cached

        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'key': self.google_api_key,
            'place_id': place_id,
            'fields': 'name,formatted_address,rating,price_level,photos,types'
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            data = response.json()

            if data.get('status') == 'OK':
                result = data.get('result', {})
                self._save_cache(cache_path, result)
                self._add_cost('place_details')
                return result

        except Exception as e:
            print(f"Details error: {e}")

        return None

    def download_photo(self, photo_reference: str, save_path: Path, max_width: int = 1600) -> bool:
        """Download a single photo"""
        if not self._check_budget():
            return False

        url = "https://maps.googleapis.com/maps/api/place/photo"
        params = {
            'maxwidth': max_width,
            'photoreference': photo_reference,
            'key': self.google_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                self._add_cost('place_photo')
                self.photos_downloaded += 1
                return True

        except Exception as e:
            print(f"Download error: {e}")

        return False

    def download_restaurant_photos(self, name: str, lat: float, lon: float,
                                   max_photos: int = 10, farm_id: Optional[int] = None) -> Dict:
        """
        Download photos for a restaurant

        Returns:
            Dict with restaurant info and photo paths
        """
        # Create safe directory name
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()[:50]

        if farm_id is not None:
            restaurant_dir = self.photos_dir / f"farm_{farm_id}" / safe_name
        else:
            restaurant_dir = self.photos_dir / safe_name

        result = {
            'name': name,
            'lat': lat,
            'lon': lon,
            'place_id': None,
            'details': None,
            'photo_files': [],
            'errors': [],
            'image_dir': str(restaurant_dir)
        }

        # Check if already processed
        report_path = restaurant_dir / "photo_info.json"
        if report_path.exists():
            print(f"    [Skipping - already downloaded]")
            return self._load_cache(report_path)

        # Find Place ID
        place_id = self.find_place_by_location(name, lat, lon)
        if not place_id:
            result['errors'].append("Place not found")
            return result

        result['place_id'] = place_id

        # Get details
        details = self.get_place_details(place_id)
        if not details:
            result['errors'].append("Details not found")
            return result

        result['details'] = {
            'name': details.get('name'),
            'address': details.get('formatted_address'),
            'rating': details.get('rating'),
            'price_level': details.get('price_level'),
            'types': details.get('types', [])
        }

        # Download photos
        photos = details.get('photos', [])[:max_photos]
        print(f"    Found {len(photos)} photos")

        for i, photo in enumerate(photos):
            photo_ref = photo.get('photo_reference')
            if not photo_ref:
                continue

            photo_filename = f"photo_{i+1}_{photo_ref[:10]}.jpg"
            photo_path = restaurant_dir / photo_filename

            print(f"    Downloading photo {i+1}/{len(photos)}...")
            if self.download_photo(photo_ref, photo_path):
                result['photo_files'].append(str(photo_path))
                print(f"      Saved: {photo_filename}")

            time.sleep(0.2)  # Rate limiting

        # Save info
        restaurant_dir.mkdir(parents=True, exist_ok=True)
        self._save_cache(report_path, result)
        self.restaurants_processed += 1

        return result

    def process_farm(self, farm_id: int, food_poi: gpd.GeoDataFrame,
                    connections: gpd.GeoDataFrame, max_photos_per_restaurant: int = 10) -> Dict:
        """
        Process all restaurants connected to a farm
        """
        # Get connected food POIs
        farm_connections = connections[connections['farm_id'] == farm_id]
        food_connections = farm_connections[farm_connections['poi_type'] == 'food']

        print(f"\n  Farm {farm_id}: {len(food_connections)} restaurants to process")

        results = []
        for idx, conn in food_connections.iterrows():
            if not self._check_budget():
                break

            # Find matching POI
            poi_idx = food_poi.geometry.sindex.nearest(conn.geometry, return_all=False)
            if len(poi_idx) > 0:
                poi = food_poi.iloc[poi_idx[0]]

                # Convert to WGS84
                poi_wgs84 = food_poi.iloc[[poi_idx[0]]].to_crs(CRS_GEOGRAPHIC).iloc[0]
                lat = float(poi_wgs84.geometry.y)
                lon = float(poi_wgs84.geometry.x)

                print(f"    [{len(results)+1}/{len(food_connections)}] {poi['name']} ({lat:.4f}, {lon:.4f})")

                result = self.download_restaurant_photos(
                    poi['name'], lat, lon,
                    max_photos=max_photos_per_restaurant,
                    farm_id=farm_id
                )
                results.append(result)

        return {
            'farm_id': farm_id,
            'restaurants_processed': len(results),
            'total_photos': sum(len(r['photo_files']) for r in results),
            'restaurants': results
        }


def main():
    """Download photos for Phase 1 farms"""
    print("="*60)
    print("PHOTO DOWNLOADER - Phase 1 Farms")
    print("="*60)

    # Set API key via environment variable: export GOOGLE_PLACES_API_KEY=your_key
    if not os.environ.get('GOOGLE_PLACES_API_KEY'):
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable not set")
        return

    # Initialize downloader
    downloader = PhotoDownloader(budget_limit=385.0)

    # Load data
    print("\nLoading data...")
    farms = gpd.read_file('json/farms_phase_clustered.geojson')
    food_poi = gpd.read_file('json/food.geojson')
    connections = gpd.read_file('network_connections_400m.geojson')

    print(f"  Farms: {len(farms)}")
    print(f"  Food POI: {len(food_poi)}")
    print(f"  Connections: {len(connections)}")

    # Get Phase 1 farms
    phase1_farms = farms[farms['phase'] == 1].sort_values('farm_id')
    print(f"\nPhase 1 farms: {len(phase1_farms)}")

    # Process each farm
    all_results = []
    for farm_id in phase1_farms['farm_id'].values:
        if not downloader._check_budget():
            print("\nBudget exhausted, stopping...")
            break

        print(f"\n{'='*60}")
        print(f"Processing Farm {farm_id}")
        print(f"Budget: ${downloader.total_cost:.2f} / ${downloader.budget_limit:.2f}")
        print(f"{'='*60}")

        result = downloader.process_farm(
            farm_id, food_poi, connections,
            max_photos_per_restaurant=10
        )
        all_results.append(result)

        # Save progress
        progress_path = downloader.cache_dir / "download_progress.json"
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_cost': downloader.total_cost,
                'photos_downloaded': downloader.photos_downloaded,
                'restaurants_processed': downloader.restaurants_processed,
                'farms_completed': [r['farm_id'] for r in all_results],
                'results': all_results
            }, f, ensure_ascii=False, indent=2)

    # Final summary
    print("\n" + "="*60)
    print("DOWNLOAD COMPLETE")
    print("="*60)
    print(f"  Total cost: ${downloader.total_cost:.2f}")
    print(f"  Photos downloaded: {downloader.photos_downloaded}")
    print(f"  Restaurants processed: {downloader.restaurants_processed}")
    print(f"  Farms completed: {len(all_results)}")


if __name__ == "__main__":
    main()
