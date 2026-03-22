"""
Phase 1 Automation Script
- Download restaurant photos from Google Places API
- Analyze with MCP (via Claude Code)
- Generate linked report

Budget: ~$185 for 1557 restaurants
"""

import os
import sys
sys.stdout.reconfigure(encoding='utf-8')

import json
import time
import requests
from typing import Optional, Dict, List, Set
from pathlib import Path
import hashlib
import geopandas as gpd
import pandas as pd
from pyproj import CRS


# Google Places API Pricing (March 2025)
PRICING = {
    'nearby_search': 0.032,
    'place_details': 0.017,
    'place_photo': 0.007,
}

CRS_GEOGRAPHIC = CRS.from_epsg(4326)


class Phase1Automation:
    """Automate Phase 1 photo download and analysis preparation"""

    def __init__(self,
                 google_api_key: Optional[str] = None,
                 cache_dir: str = "cache/restaurant_photos",
                 budget_limit: float = 385.0,
                 max_photos_per_restaurant: int = 5):
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir = self.cache_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)

        self.budget_limit = budget_limit
        self.max_photos = max_photos_per_restaurant
        self.total_cost = 0.0
        self.api_calls = {'nearby_search': 0, 'place_details': 0, 'place_photo': 0}
        self.photos_downloaded = 0
        self.restaurants_processed = 0
        self.restaurants_skipped = 0

    def _check_budget(self) -> bool:
        return self.total_cost < self.budget_limit

    def _add_cost(self, api_type: str):
        cost = PRICING.get(api_type, 0)
        self.total_cost += cost
        self.api_calls[api_type] += 1

    def _get_cache_path(self, prefix: str, key: str) -> Path:
        cache_key = hashlib.md5(f"{prefix}_{key}".encode()).hexdigest()
        return self.cache_dir / f"{prefix}_{cache_key}.json"

    def _load_cache(self, cache_path: Path) -> Optional[Dict]:
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_path: Path, data: Dict):
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def find_place_by_location(self, name: str, lat: float, lon: float, radius: int = 200) -> Optional[str]:
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
                print("\n  [RATE LIMIT] Waiting 5 minutes...")
                time.sleep(300)
                return self.find_place_by_location(name, lat, lon, radius)

        except Exception as e:
            print(f"  [ERROR] Search failed: {e}")

        return None

    def get_place_details(self, place_id: str) -> Optional[Dict]:
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
            print(f"  [ERROR] Details failed: {e}")

        return None

    def download_photo(self, photo_reference: str, save_path: Path, max_width: int = 800) -> bool:
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
            print(f"  [ERROR] Photo download failed: {e}")

        return False

    def process_restaurant(self, name: str, lat: float, lon: float, farm_id: int) -> Dict:
        """Process a single restaurant - download photos only (no VLM analysis)"""
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()[:50]
        restaurant_dir = self.photos_dir / f"farm_{farm_id}" / safe_name

        result = {
            'name': name,
            'lat': lat,
            'lon': lon,
            'farm_id': farm_id,
            'place_id': None,
            'photo_files': [],
            'errors': []
        }

        # Check if already processed
        report_path = restaurant_dir / "photo_info.json"
        if report_path.exists():
            self.restaurants_skipped += 1
            return self._load_cache(report_path)

        if not self._check_budget():
            result['errors'].append("Budget exhausted")
            return result

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

        # Download photos
        photos = details.get('photos', [])[:self.max_photos]

        for i, photo in enumerate(photos):
            photo_ref = photo.get('photo_reference')
            if not photo_ref:
                continue

            photo_filename = f"photo_{i+1}_{photo_ref[:10]}.jpg"
            photo_path = restaurant_dir / photo_filename

            if self.download_photo(photo_ref, photo_path):
                result['photo_files'].append(str(photo_path))

            time.sleep(0.1)  # Rate limiting

        # Save info
        restaurant_dir.mkdir(parents=True, exist_ok=True)
        self._save_cache(report_path, result)
        self.restaurants_processed += 1

        return result

    def get_phase1_restaurants(self) -> List[Dict]:
        """Get all unique restaurants connected to Phase 1 farms"""
        print("Loading data...")
        connections = gpd.read_file('network_visualization/network_connections_400m.geojson')
        food_poi = gpd.read_file('json/food.geojson')

        # Phase 1 food connections
        phase1_food = connections[(connections['phase'] == 1) & (connections['poi_type'] == 'food')]
        print(f"  Phase 1 food connections: {len(phase1_food)}")

        # Match to food POI
        restaurants = []
        seen = set()

        for idx, conn in phase1_food.iterrows():
            distances = food_poi.geometry.distance(conn.geometry)
            nearest_idx = distances.idxmin()

            if distances.min() < 0.001:  # ~100m threshold in degrees
                poi = food_poi.loc[nearest_idx]
                key = (poi['name'], round(poi['latitude'], 5), round(poi['longitude'], 5))

                if key not in seen:
                    seen.add(key)
                    restaurants.append({
                        'name': poi['name'],
                        'lat': poi['latitude'],
                        'lon': poi['longitude'],
                        'farm_id': conn['farm_id'],
                        'subcategory': poi.get('subcategor', 'restaurant')
                    })

        print(f"  Unique restaurants: {len(restaurants)}")
        return restaurants

    def run(self, limit: Optional[int] = None):
        """Run Phase 1 automation"""
        print("=" * 60)
        print("PHASE 1 AUTOMATION")
        print("=" * 60)

        restaurants = self.get_phase1_restaurants()

        if limit:
            restaurants = restaurants[:limit]
            print(f"\n[LIMIT] Processing only {limit} restaurants")

        print(f"\nBudget: ${self.budget_limit}")
        print(f"Max photos per restaurant: {self.max_photos}")
        print(f"Estimated cost: ${len(restaurants) * (PRICING['nearby_search'] + PRICING['place_details'] + self.max_photos * PRICING['place_photo']):.2f}")

        # Process restaurants
        results = []
        for i, r in enumerate(restaurants):
            if not self._check_budget():
                print("\n[BUDGET EXHAUSTED]")
                break

            print(f"\n[{i+1}/{len(restaurants)}] {r['name']} (Farm {r['farm_id']})")
            print(f"  Cost so far: ${self.total_cost:.2f}")

            result = self.process_restaurant(r['name'], r['lat'], r['lon'], r['farm_id'])
            results.append(result)

            if result['photo_files']:
                print(f"  Downloaded {len(result['photo_files'])} photos")
            elif result['errors']:
                print(f"  Errors: {result['errors']}")

            # Save progress every 50 restaurants
            if (i + 1) % 50 == 0:
                self._save_progress(results)

        # Final save
        self._save_progress(results)

        # Summary
        print("\n" + "=" * 60)
        print("DOWNLOAD COMPLETE")
        print("=" * 60)
        print(f"  Restaurants processed: {self.restaurants_processed}")
        print(f"  Restaurants skipped (cached): {self.restaurants_skipped}")
        print(f"  Photos downloaded: {self.photos_downloaded}")
        print(f"  Total cost: ${self.total_cost:.2f}")
        print(f"  API calls: {self.api_calls}")

        return results

    def _save_progress(self, results: List[Dict]):
        progress_path = self.cache_dir / "phase1_progress.json"
        with open(progress_path, 'w', encoding='utf-8') as f:
            json.dump({
                'total_cost': self.total_cost,
                'api_calls': self.api_calls,
                'photos_downloaded': self.photos_downloaded,
                'restaurants_processed': self.restaurants_processed,
                'restaurants_skipped': self.restaurants_skipped,
                'results': results
            }, f, ensure_ascii=False, indent=2)
        print(f"  [Progress saved]")


def main():
    # Set API key
    # Set API key via environment variable: export GOOGLE_PLACES_API_KEY=your_key
    if not os.environ.get('GOOGLE_PLACES_API_KEY'):
        print("ERROR: GOOGLE_PLACES_API_KEY environment variable not set")
        return

    # Initialize
    automation = Phase1Automation(
        budget_limit=385.0,
        max_photos_per_restaurant=5  # Reduce cost
    )

    # Run (set limit=None for full run)
    automation.run(limit=None)


if __name__ == "__main__":
    main()
