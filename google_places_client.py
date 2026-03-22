"""
Google Places API Client for Restaurant Menu Analysis
获取餐厅详情和菜单信息
"""

import os
import json
import time
import requests
from typing import Optional, Dict, List, Any
from pathlib import Path
import hashlib


class GooglePlacesClient:
    """Google Places API 封装类"""

    BASE_URL = "https://maps.googleapis.com/maps/api/place"

    def __init__(self, api_key: Optional[str] = None, cache_dir: str = "cache/places"):
        """
        初始化 Google Places API 客户端

        Args:
            api_key: Google Places API Key (也可通过环境变量 GOOGLE_PLACES_API_KEY 设置)
            cache_dir: 缓存目录，用于存储 API 响应以节省配额
        """
        self.api_key = api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        if not self.api_key:
            print("Warning: No Google Places API key provided. Set GOOGLE_PLACES_API_KEY environment variable.")

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # API 调用统计
        self.calls_made = 0
        self.cache_hits = 0

    def _get_cache_path(self, endpoint: str, params: Dict) -> Path:
        """生成缓存文件路径"""
        param_str = json.dumps(params, sort_keys=True)
        cache_key = hashlib.md5(f"{endpoint}_{param_str}".encode()).hexdigest()
        return self.cache_dir / f"{endpoint}_{cache_key}.json"

    def _load_cache(self, cache_path: Path) -> Optional[Dict]:
        """从缓存加载数据"""
        if cache_path.exists():
            with open(cache_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def _save_cache(self, cache_path: Path, data: Dict):
        """保存数据到缓存"""
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _make_request(self, endpoint: str, params: Dict, use_cache: bool = True) -> Optional[Dict]:
        """
        发送 API 请求

        Args:
            endpoint: API 端点 (如 "nearbysearch", "details")
            params: 请求参数
            use_cache: 是否使用缓存

        Returns:
            API 响应字典或 None
        """
        if not self.api_key:
            return None

        params['key'] = self.api_key
        cache_path = self._get_cache_path(endpoint, params)

        # 检查缓存
        if use_cache:
            cached = self._load_cache(cache_path)
            if cached:
                self.cache_hits += 1
                return cached

        # 发送请求
        url = f"{self.BASE_URL}/{endpoint}/json"
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get('status') not in ['OK', 'ZERO_RESULTS']:
                print(f"API Error: {data.get('status')} - {data.get('error_message', 'Unknown error')}")
                return None

            self.calls_made += 1

            # 保存到缓存
            if use_cache:
                self._save_cache(cache_path, data)

            return data

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            return None

    def find_place_by_location(self, name: str, lat: float, lon: float, radius: int = 50) -> Optional[str]:
        """
        通过名称和位置查找 Place ID

        Args:
            name: 餐厅名称
            lat: 纬度
            lon: 经度
            radius: 搜索半径 (米)

        Returns:
            Place ID 或 None
        """
        # 使用 Nearby Search
        params = {
            'location': f"{lat},{lon}",
            'radius': radius,
            'name': name,
            'type': 'restaurant'
        }

        data = self._make_request('nearbysearch', params)
        if data and data.get('results'):
            # 返回最匹配的结果
            for result in data['results']:
                if name.lower() in result.get('name', '').lower():
                    return result.get('place_id')
            # 如果没有精确匹配，返回第一个结果
            return data['results'][0].get('place_id')

        return None

    def get_place_details(self, place_id: str, fields: Optional[List[str]] = None) -> Optional[Dict]:
        """
        获取地点详情

        Args:
            place_id: Google Place ID
            fields: 请求的字段列表

        Returns:
            地点详情字典
        """
        if fields is None:
            fields = [
                'name',
                'formatted_address',
                'international_phone_number',
                'website',
                'opening_hours',
                'price_level',
                'rating',
                'user_ratings_total',
                'serves_breakfast',
                'serves_lunch',
                'serves_dinner',
                'serves_vegetarian_food',
                'serves_wine',
                'dine_in',
                'takeout',
                'delivery',
                # Note: Google Places API 不直接提供菜单
                # 但我们可以从其他来源推断
            ]

        params = {
            'place_id': place_id,
            'fields': ','.join(fields)
        }

        data = self._make_request('details', params)
        if data and data.get('result'):
            return data['result']

        return None

    def get_restaurant_info(self, name: str, lat: float, lon: float) -> Optional[Dict]:
        """
        获取餐厅信息（综合查找和详情）

        Args:
            name: 餐厅名称
            lat: 纬度
            lon: 经度

        Returns:
            餐厅信息字典
        """
        # 首先查找 Place ID
        place_id = self.find_place_by_location(name, lat, lon)
        if not place_id:
            return None

        # 获取详情
        details = self.get_place_details(place_id)
        if details:
            return {
                'place_id': place_id,
                'name': details.get('name'),
                'address': details.get('formatted_address'),
                'phone': details.get('international_phone_number'),
                'website': details.get('website'),
                'rating': details.get('rating'),
                'price_level': details.get('price_level'),
                'opening_hours': details.get('opening_hours', {}).get('weekday_text', []),
                'serves_breakfast': details.get('serves_breakfast'),
                'serves_lunch': details.get('serves_lunch'),
                'serves_dinner': details.get('serves_dinner'),
                'vegetarian': details.get('serves_vegetarian_food'),
                'dine_in': details.get('dine_in'),
                'takeout': details.get('takeout'),
                'delivery': details.get('delivery'),
            }

        return None

    def extract_potential_ingredients(self, restaurant_info: Dict, subcategory: str) -> List[str]:
        """
        根据餐厅类型和子类别推断可能需要的食材

        Args:
            restaurant_info: 餐厅信息
            subcategory: 餐厅子类别 (fast_food, restaurant, cafe, etc.)

        Returns:
            可能需要的食材列表
        """
        ingredients = set()

        # 根据子类别推断食材
        subcategory_ingredients = {
            'fast_food': [
                'lettuce', 'tomato', 'onion', 'potato', 'chicken',
                'beef', 'cheese', 'bread', 'eggs'
            ],
            'restaurant': [
                'leafy_greens', 'tomato', 'herbs', 'vegetables',
                'citrus', 'ginger', 'garlic', 'chili'
            ],
            'cafe': [
                'herbs', 'lettuce', 'tomato', 'eggs', 'cheese',
                'bread', 'fruits'
            ],
            'food_court': [
                'leafy_greens', 'vegetables', 'herbs', 'rice_herbs',
                'asian_greens', 'chili', 'ginger', 'garlic'
            ],
            'bar': [
                'herbs', 'citrus', 'fruits', 'leafy_greens'
            ]
        }

        if subcategory in subcategory_ingredients:
            ingredients.update(subcategory_ingredients[subcategory])

        # 根据服务类型推断
        if restaurant_info:
            if restaurant_info.get('vegetarian'):
                ingredients.update(['leafy_greens', 'vegetables', 'herbs', 'mushrooms'])

            if restaurant_info.get('serves_breakfast'):
                ingredients.update(['eggs', 'tomato', 'herbs', 'mushrooms'])

        return list(ingredients)

    def get_stats(self) -> Dict:
        """获取 API 调用统计"""
        return {
            'calls_made': self.calls_made,
            'cache_hits': self.cache_hits,
            'total_requests': self.calls_made + self.cache_hits
        }


def main():
    """测试 Google Places API 客户端"""
    client = GooglePlacesClient()

    # 测试：查找餐厅信息
    test_cases = [
        ("Jumbo Seafood", 1.2892592, 103.8482726),
        ("McDonald's", 1.3967854, 103.8872571),
    ]

    for name, lat, lon in test_cases:
        print(f"\nSearching for: {name}")
        info = client.get_restaurant_info(name, lat, lon)
        if info:
            print(f"  Found: {info['name']}")
            print(f"  Rating: {info.get('rating', 'N/A')}")
            print(f"  Address: {info.get('address', 'N/A')}")
        else:
            print("  Not found")

    print(f"\nAPI Stats: {client.get_stats()}")


if __name__ == "__main__":
    main()
