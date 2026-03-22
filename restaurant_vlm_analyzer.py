"""
Restaurant Photo Analyzer with VLM
获取餐厅照片并使用 VLM 分析菜单和食材
"""

import os
import json
import time
import requests
import base64
from typing import Optional, Dict, List, Any
from pathlib import Path
import hashlib
from io import BytesIO


class RestaurantPhotoAnalyzer:
    """餐厅照片分析器 - 使用 Google Places API 获取照片，VLM 分析"""

    # Google Places API Pricing (March 2025)
    # Source: https://developers.google.com/maps/documentation/places/web-service/usage-and-billing
    PRICING = {
        'nearby_search': 0.032,    # $0.032 per call ($32/1000)
        'place_details': 0.017,    # $0.017 per call ($17/1000)
        'place_photo': 0.007,      # $0.007 per call ($7/1000)
    }

    def __init__(self,
                 google_api_key: Optional[str] = None,
                 vlm_api_key: Optional[str] = None,
                 vlm_api_base: str = "https://open.bigmodel.cn/api/anthropic",
                 vlm_model: str = "glm-4.6v",
                 cache_dir: str = "cache/restaurant_photos",
                 budget_limit: float = 200.0):
        """
        初始化分析器

        Args:
            google_api_key: Google Places API Key
            vlm_api_key: VLM API Key
            vlm_api_base: VLM API Base URL
            vlm_model: VLM 模型名称
            cache_dir: 缓存目录
            budget_limit: Google API 预算上限 (美元)
        """
        self.google_api_key = google_api_key or os.environ.get("GOOGLE_PLACES_API_KEY")
        self.vlm_api_key = vlm_api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.vlm_api_base = vlm_api_base
        self.vlm_model = vlm_model
        self.budget_limit = budget_limit

        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.photos_dir = self.cache_dir / "photos"
        self.photos_dir.mkdir(exist_ok=True)

        # API 调用统计
        self.places_calls = 0
        self.vlm_calls = 0
        self.cache_hits = 0
        self.photo_downloads = 0

        # 成本追踪
        self.total_cost = 0.0

    def _check_budget(self) -> bool:
        """检查是否超出预算"""
        if self.total_cost >= self.budget_limit:
            print(f"\n{'='*60}")
            print(f"BUDGET LIMIT REACHED: ${self.total_cost:.2f} / ${self.budget_limit:.2f}")
            print(f"{'='*60}\n")
            return False
        return True

    def _add_cost(self, api_type: str):
        """添加 API 调用成本"""
        cost = self.PRICING.get(api_type, 0)
        self.total_cost += cost
        if self.total_cost % 1.0 < cost:  # Print every ~$1
            print(f"    [Cost so far: ${self.total_cost:.2f} / ${self.budget_limit:.2f}]")

    def _get_cache_path(self, prefix: str, key: str) -> Path:
        """生成缓存文件路径"""
        cache_key = hashlib.md5(f"{prefix}_{key}".encode()).hexdigest()
        return self.cache_dir / f"{prefix}_{cache_key}.json"

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

    def find_place_by_location(self, name: str, lat: float, lon: float, radius: int = 200) -> Optional[str]:
        """通过名称和位置查找 Place ID"""
        print(f"    Searching at: ({lat:.6f}, {lon:.6f})")

        if not self.google_api_key:
            print("    ERROR: No Google API key")
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
            status = data.get('status')
            results_count = len(data.get('results', []))
            print(f"    API status: {status}, results: {results_count}")

            if data.get('status') == 'OK' and data.get('results'):
                # 返回最匹配的结果
                for result in data['results']:
                    if name.lower() in result.get('name', '').lower():
                        print(f"  Found match: {result.get('name')}")
                        return result.get('place_id')
                # 如果没有精确匹配，返回第一个结果
                print(f"  Using first result: {data['results'][0].get('name')}")
                return data['results'][0].get('place_id')

            elif data.get('status') == 'OVER_QUERY_LIMIT':
                # Rate limit hit - wait 5 hours and retry
                print(f"\n{'='*60}")
                print("GOOGLE API RATE LIMIT HIT - Waiting 5 hours before retry...")
                print(f"{'='*60}\n")
                import time
                time.sleep(5 * 60 * 60)  # 5 hours in seconds
                return self.find_place_by_location(name, lat, lon, radius)

            self.places_calls += 1
        except Exception as e:
            print(f"Place search error: {e}")

        return None

    def get_place_details_with_photos(self, place_id: str) -> Optional[Dict]:
        """获取地点详情和照片引用"""
        if not self.google_api_key:
            return None

        cache_path = self._get_cache_path("details", place_id)
        cached = self._load_cache(cache_path)
        if cached:
            self.cache_hits += 1
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
            print(f"  Details API status: {data.get('status')}")

            if data.get('status') == 'OK':
                result = data.get('result', {})
                self._save_cache(cache_path, result)
                self.places_calls += 1
                return result
            else:
                print(f"  Details API error: {data.get('error_message', data.get('status'))}")
        except Exception as e:
            print(f"Details fetch error: {e}")

        return None

    def get_photo_url(self, photo_reference: str, max_width: int = 400) -> Optional[str]:
        """获取照片 URL"""
        if not self.google_api_key:
            return None

        return (
            f"https://maps.googleapis.com/maps/api/place/photo?"
            f"maxwidth={max_width}&photoreference={photo_reference}&key={self.google_api_key}"
        )

    def download_photo(self, photo_reference: str, max_width: int = 1600,
                       save_path: Optional[Path] = None) -> Optional[bytes]:
        """下载照片并可选保存到文件（使用高分辨率以便VLM识别细节）"""
        if not self.google_api_key:
            return None

        url = "https://maps.googleapis.com/maps/api/place/photo"
        params = {
            'maxwidth': max_width,
            'photoreference': photo_reference,
            'key': self.google_api_key
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 200:
                image_data = response.content

                # 保存到文件
                if save_path:
                    save_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(save_path, 'wb') as f:
                        f.write(image_data)
                    print(f"    Saved: {save_path.name} ({len(image_data)//1024}KB)")

                return image_data
        except Exception as e:
            print(f"Photo download error: {e}")

        return None

    def analyze_photo_with_vlm(self, image_data: bytes, analysis_type: str = "food") -> Optional[Dict]:
        """
        使用 VLM 分析照片

        Args:
            image_data: 图片二进制数据
            analysis_type: 分析类型 ("menu" 或 "food")

        Returns:
            分析结果
        """
        if not self.vlm_api_key:
            return None

        # 转换为 base64
        image_base64 = base64.b64encode(image_data).decode('utf-8')

        # 根据分析类型选择提示词
        if analysis_type == "menu":
            prompt = """You are an urban farming consultant analyzing restaurant menus for Singapore urban farms.

Analyze this image and extract information relevant to LOCAL URBAN FARMING. Answer in JSON format:
{
    "is_menu": true/false,
    "restaurant_type": "hawker/fine_dining/fast_food/cafe/etc",
    "cuisine_type": "Chinese/Malay/Indian/Western/Japanese/Fusion/etc",
    "menu_items": [
        {
            "name": "dish name",
            "price_range": "budget/mid/premium",
            "key_ingredients": ["ingredient1", "ingredient2"]
        }
    ],
    "farmable_ingredients": {
        "leafy_greens": ["kangkong", "kai lan", "spinach", "lettuce", "bok choy", "chye sim"],
        "herbs": ["curry leaf", "laksa leaf", "chinese celery", "coriander", "basil", "mint", "lemongrass", "pandan"],
        "aromatics": ["ginger", "garlic", "shallot", "chili", "galangal", "turmeric"],
        "vegetables": ["eggplant", "cucumber", "bitter gourd", "luffa", "long beans", "okra"],
        "fruits": ["tomato", "chili pepper", "lime", "papaya", "banana"]
    },
    "high_demand_ingredients": ["ingredients frequently used across multiple dishes"],
    "import_substitution_potential": ["ingredients currently imported but could be grown locally"],
    "urban_farming_recommendations": "specific recommendations for what to grow based on this menu",
    "notes": "any other observations relevant to urban farming"
}

Focus on ingredients that:
1. Are commonly used in Singaporean/Malaysian cuisine
2. Can be grown in tropical climate (hot, humid, year-round)
3. Are suitable for rooftop/podium/streetscape farming
4. Have short growing cycles (30-90 days preferred)
5. Are currently imported and could be substituted with local production

If this is not a menu image, set is_menu to false and describe what you see instead."""
        else:  # food
            prompt = """You are an urban farming consultant analyzing food photos for Singapore urban farms.

Analyze this food image and extract information relevant to LOCAL URBAN FARMING. Answer in JSON format:
{
    "is_food": true/false,
    "dish_name": "name of the dish if identifiable",
    "cuisine_type": "Chinese/Malay/Indian/Western/Japanese/Fusion/etc",
    "visible_ingredients": [
        {
            "name": "ingredient name",
            "confidence": "high/medium/low",
            "form": "fresh/dried/pickled/cooked"
        }
    ],
    "farmable_in_singapore": {
        "leafy_greens": {
            "items": ["e.g., kangkong, chye sim, kai lan"],
            "growing_difficulty": "easy/moderate/hard",
            "days_to_harvest": "estimated days"
        },
        "herbs": {
            "items": ["e.g., curry leaf, laksa leaf, basil, coriander"],
            "growing_difficulty": "easy/moderate/hard",
            "days_to_harvest": "estimated days"
        },
        "aromatics": {
            "items": ["e.g., ginger, garlic, chili, lemongrass"],
            "growing_difficulty": "easy/moderate/hard",
            "days_to_harvest": "estimated days"
        },
        "vegetables": {
            "items": ["e.g., eggplant, long beans, okra"],
            "growing_difficulty": "easy/moderate/hard",
            "days_to_harvest": "estimated days"
        }
    },
    "growing_recommendations": {
        "best_for_rooftop": ["crops suitable for rooftop with full sun"],
        "best_for_podium": ["crops suitable for partial shade podium areas"],
        "best_for_streetscape": ["crops suitable for streetscape with limited space"],
        "quick_wins": ["crops with fastest turnaround time"]
    },
    "local_sourcing_potential": {
        "highly_suitable": ["ingredients that are easy to grow locally"],
        "moderately_suitable": ["ingredients that need some care but feasible"],
        "not_suitable": ["ingredients that cannot be grown in Singapore climate"]
    },
    "vegetarian_friendly": true/false,
    "notes": "any other observations about the dish and farming potential"
}

IMPORTANT GUIDELINES:
1. Focus on SINGAPORE/MALAYSIA common ingredients (tropical climate, zone 10-11)
2. Consider urban constraints: limited space, rooftop heat, wind exposure
3. Prioritize: leafy greens > herbs > aromatics > vegetables (by ease of growing)
4. Note ingredients that are currently imported and could be locally substituted
5. Consider the growing form - hydroponic vs soil-based suitability

If this is not a food image, set is_food to false and describe what you see instead."""

        headers = {
            'x-api-key': self.vlm_api_key,
            'anthropic-version': '2023-06-01',
            'Content-Type': 'application/json'
        }

        data = {
            'model': self.vlm_model,
            'max_tokens': 800,
            'messages': [{
                'role': 'user',
                'content': [
                    {'type': 'text', 'text': prompt},
                    {
                        'type': 'image',
                        'source': {
                            'type': 'base64',
                            'media_type': 'image/jpeg',
                            'data': image_base64
                        }
                    }
                ]
            }]
        }

        try:
            response = requests.post(
                f"{self.vlm_api_base}/v1/messages",
                headers=headers,
                json=data,
                timeout=60
            )

            if response.status_code == 200:
                result = response.json()
                self.vlm_calls += 1
                text_response = result['content'][0]['text']

                # 尝试解析 JSON
                import re
                json_match = re.search(r'\{[\s\S]*\}', text_response)
                if json_match:
                    return json.loads(json_match.group())
                return {'raw_response': text_response}

            elif response.status_code == 429:
                # Rate limit hit - wait 5 hours and retry
                print(f"\n{'='*60}")
                print("API RATE LIMIT HIT - Waiting 5 hours before retry...")
                print(f"{'='*60}")
                import time
                time.sleep(5 * 60 * 60)  # 5 hours in seconds
                # Retry after waiting
                return self.analyze_photo_with_vlm(image_data, analysis_type)

            else:
                print(f"VLM error: {response.status_code} - {response.text[:200]}")

        except Exception as e:
            print(f"VLM call error: {e}")

        return None

    def analyze_restaurant(self, name: str, lat: float, lon: float,
                          max_photos: int = 5, farm_id: Optional[int] = None) -> Dict:
        """
        完整分析一个餐厅

        Args:
            name: 餐厅名称
            lat: 纬度
            lon: 经度
            max_photos: 最大分析照片数
            farm_id: 关联的 farm ID（用于组织图片存储）

        Returns:
            分析结果
        """
        # 创建餐厅专属目录
        safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name[:50]  # 限制长度

        if farm_id is not None:
            restaurant_dir = self.photos_dir / f"farm_{farm_id}" / safe_name
        else:
            restaurant_dir = self.photos_dir / safe_name

        restaurant_dir.mkdir(parents=True, exist_ok=True)

        result = {
            'name': name,
            'lat': lat,
            'lon': lon,
            'place_id': None,
            'details': None,
            'photos_analyzed': 0,
            'photo_analysis': [],
            'photo_files': [],  # 保存的照片文件列表
            'aggregated_ingredients': [],
            'cuisine_types': [],
            'errors': [],
            'image_dir': str(restaurant_dir)
        }

        # 1. 查找 Place ID
        print(f"  Searching for: {name}")
        place_id = self.find_place_by_location(name, lat, lon)
        if not place_id:
            result['errors'].append("Place not found")
            return result

        result['place_id'] = place_id

        # 2. 获取详情和照片
        details = self.get_place_details_with_photos(place_id)
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

        # 3. 分析照片
        photos = details.get('photos', [])[:max_photos]
        print(f"  Found {len(photos)} photos to analyze")

        all_ingredients = set()
        all_cuisines = set()
        all_farmable = {
            'leafy_greens': [],
            'herbs': [],
            'aromatics': [],
            'vegetables': []
        }
        growing_recommendations = {
            'best_for_rooftop': [],
            'best_for_podium': [],
            'best_for_streetscape': [],
            'quick_wins': []
        }

        for i, photo in enumerate(photos):
            photo_ref = photo.get('photo_reference')
            if not photo_ref:
                continue

            # 下载并保存照片
            photo_filename = f"photo_{i+1}_{photo_ref[:10]}.jpg"
            photo_path = restaurant_dir / photo_filename

            print(f"  Downloading photo {i+1}/{len(photos)}...")
            image_data = self.download_photo(photo_ref, save_path=photo_path)
            if not image_data:
                continue

            result['photo_files'].append(str(photo_path))

            # 分析照片
            print(f"  Analyzing photo {i+1} with VLM...")
            analysis = self.analyze_photo_with_vlm(image_data, analysis_type="food")
            if analysis:
                # 添加照片元数据
                analysis['photo_file'] = str(photo_path)
                analysis['photo_index'] = i + 1
                result['photo_analysis'].append(analysis)
                result['photos_analyzed'] += 1

                # 收集食材 (新版格式)
                if analysis.get('visible_ingredients'):
                    for ing in analysis['visible_ingredients']:
                        if isinstance(ing, dict):
                            all_ingredients.add(ing.get('name', ''))
                        else:
                            all_ingredients.add(ing)

                # 收集可种植食材 (新版格式)
                farmable = analysis.get('farmable_in_singapore', {})
                for category in ['leafy_greens', 'herbs', 'aromatics', 'vegetables']:
                    if farmable.get(category, {}).get('items'):
                        all_farmable[category].extend(farmable[category]['items'])

                # 收集种植建议
                recs = analysis.get('growing_recommendations', {})
                for rec_type in ['best_for_rooftop', 'best_for_podium', 'best_for_streetscape', 'quick_wins']:
                    if recs.get(rec_type):
                        growing_recommendations[rec_type].extend(recs[rec_type])

                if analysis.get('cuisine_type'):
                    all_cuisines.add(analysis['cuisine_type'])

            # 避免频繁调用
            time.sleep(0.3)

        # 去重
        result['aggregated_ingredients'] = list(all_ingredients)
        result['cuisine_types'] = list(all_cuisines)
        result['farmable_ingredients'] = {k: list(set(v)) for k, v in all_farmable.items()}
        result['growing_recommendations'] = {k: list(set(v)) for k, v in growing_recommendations.items()}

        # 保存餐厅分析报告
        report_path = restaurant_dir / "analysis_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        return result

    def get_stats(self) -> Dict:
        """获取 API 调用统计"""
        return {
            'places_api_calls': self.places_calls,
            'vlm_api_calls': self.vlm_calls,
            'cache_hits': self.cache_hits
        }


def main():
    """测试餐厅照片分析"""
    import argparse

    parser = argparse.ArgumentParser(description='Restaurant Photo Analyzer')
    parser.add_argument('--google-key', required=True, help='Google Places API Key')
    parser.add_argument('--vlm-key', required=True, help='VLM API Key')
    parser.add_argument('--name', required=True, help='Restaurant name')
    parser.add_argument('--lat', type=float, required=True, help='Latitude')
    parser.add_argument('--lon', type=float, required=True, help='Longitude')
    parser.add_argument('--max-photos', type=int, default=3, help='Max photos to analyze')

    args = parser.parse_args()

    analyzer = RestaurantPhotoAnalyzer(
        google_api_key=args.google_key,
        vlm_api_key=args.vlm_key
    )

    print(f"Analyzing: {args.name}")
    result = analyzer.analyze_restaurant(args.name, args.lat, args.lon, args.max_photos)

    print("\n=== Results ===")
    print(f"Place ID: {result['place_id']}")
    print(f"Photos analyzed: {result['photos_analyzed']}")
    print(f"Cuisine types: {result['cuisine_types']}")
    print(f"Ingredients: {result['aggregated_ingredients'][:20]}")

    print(f"\nAPI Stats: {analyzer.get_stats()}")


if __name__ == "__main__":
    main()
