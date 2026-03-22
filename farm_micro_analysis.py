"""
Urban Agroecology Farm Micro-Analysis
为每个 farm site 生成详细的微观分析报告
"""

import os
import geopandas as gpd
import pandas as pd
import numpy as np
from shapely.geometry import Point, LineString
from pathlib import Path
import json
import math
from typing import Dict, List, Optional, Tuple
from collections import Counter
import warnings
warnings.filterwarnings('ignore')

# 导入自定义模块
from google_places_client import GooglePlacesClient
from species_classifier import SpeciesClassifier
from restaurant_vlm_analyzer import RestaurantPhotoAnalyzer

# ============ 配置 ============
CRS_PROJECTED = 'EPSG:32648'
CRS_GEOGRAPHIC = 'EPSG:4326'
WALKING_DISTANCE = 400  # 5分钟步行距离
SPECIES_BUFFER = 1200  # 物种搜索缓冲区 (米)
OUTPUT_DIR = Path('farm_reports')
OUTPUT_DIR.mkdir(exist_ok=True)

# ============ 辅助函数 ============

def calculate_shannon_diversity(species_counts: Dict[str, int]) -> float:
    """计算 Shannon 多样性指数"""
    if not species_counts:
        return 0.0

    total = sum(species_counts.values())
    if total == 0:
        return 0.0

    shannon = 0.0
    for count in species_counts.values():
        if count > 0:
            p = count / total
            shannon -= p * math.log(p)

    return shannon


def estimate_planting_capacity(area_sqm: float, plant_type: str = 'leafy') -> int:
    """
    估算种植容量

    Args:
        area_sqm: 面积（平方米）
        plant_type: 植物类型 (leafy, root, fruit, herb)

    Returns:
        估计可种植数量
    """
    # 每种类型的平均株距（平方米/株）
    spacing = {
        'leafy': 0.25,  # 叶菜类
        'herb': 0.25,   # 香草
        'root': 0.5,    # 根茎类
        'fruit': 1.0,   # 果菜类
        'legume': 0.5,  # 豆类
    }

    # 假设 60% 的面积可用于种植
    usable_area = area_sqm * 0.6
    space_per_plant = spacing.get(plant_type, 0.5)

    return int(usable_area / space_per_plant)


class FarmMicroAnalyzer:
    """Farm 微观分析器"""

    def __init__(self, use_google_api: bool = False, use_llm_api: bool = False,
                 use_vlm_api: bool = False):
        """
        初始化分析器

        Args:
            use_google_api: 是否使用 Google Places API
            use_llm_api: 是否使用 LLM API 进行物种分类
            use_vlm_api: 是否使用 VLM API 分析餐厅照片
        """
        self.use_google_api = use_google_api
        self.use_llm_api = use_llm_api
        self.use_vlm_api = use_vlm_api

        # 初始化 API 客户端
        if use_google_api:
            self.places_client = GooglePlacesClient()
        else:
            self.places_client = None

        if use_llm_api:
            self.species_classifier = SpeciesClassifier()
        else:
            self.species_classifier = None

        if use_vlm_api:
            self.photo_analyzer = RestaurantPhotoAnalyzer(
                google_api_key=os.environ.get("GOOGLE_PLACES_API_KEY"),
                vlm_api_key=os.environ.get("ANTHROPIC_API_KEY"),
                vlm_api_base=os.environ.get("ANTHROPIC_API_BASE", "https://open.bigmodel.cn/api/anthropic"),
                vlm_model=os.environ.get("LLM_MODEL", "glm-4.6v")
            )
        else:
            self.photo_analyzer = None

        # 加载数据
        self._load_data()

    def _load_data(self):
        """加载所有必要的数据"""
        print("Loading data...")

        # Farm 数据
        self.farms = gpd.read_file('farm_with_clusters/all_farm_phases.geojson')
        self.farms = self.farms.to_crs(CRS_PROJECTED)
        print(f"  Farms: {len(self.farms)}")

        # POI 数据
        self.food_poi = gpd.read_file('json/food.geojson')
        self.food_poi = self.food_poi.to_crs(CRS_PROJECTED)
        print(f"  Food POI: {len(self.food_poi)}")

        self.social_poi = gpd.read_file('json/social_dim.geojson')
        self.social_poi = self.social_poi.to_crs(CRS_PROJECTED)
        print(f"  Social POI: {len(self.social_poi)}")

        self.cultural_poi = gpd.read_file('json/cultural_dim.geojson')
        self.cultural_poi = self.cultural_poi.to_crs(CRS_PROJECTED)
        print(f"  Cultural POI: {len(self.cultural_poi)}")

        # iNaturalist 物种数据
        self.plantae = gpd.read_file('json/inat_plantae.geojson')
        # 注意：inat_plantae 可能已经是投影坐标系
        if self.plantae.crs != CRS_PROJECTED:
            self.plantae = self.plantae.to_crs(CRS_PROJECTED)
        print(f"  Plant species: {len(self.plantae)}")

        # 网络连接数据
        self.connections = gpd.read_file('network_visualization/network_connections_400m.geojson')
        self.connections = self.connections.to_crs(CRS_PROJECTED)
        print(f"  Connection lines: {len(self.connections)}")

    def get_cluster_strategy(self, cluster_label: str) -> Dict:
        """根据 cluster 类型返回连接策略"""
        strategies = {
            'Cultural-Economic': {
                'connect_to': ['food', 'social'],
                'emphasis': 'Social Activities'
            },
            'Economic-Only': {
                'connect_to': ['food', 'social', 'cultural'],
                'emphasis': 'Social + Cultural'
            },
            'Low-Activity': {
                'connect_to': [],
                'emphasis': 'Biodiversity'
            },
            'Socio-Economic': {
                'connect_to': ['food', 'cultural'],
                'emphasis': 'Cultural Activities'
            }
        }
        return strategies.get(cluster_label, strategies['Low-Activity'])

    def analyze_farm(self, farm_id: int) -> Dict:
        """
        分析单个 farm

        Args:
            farm_id: Farm ID (对应 farms GeoDataFrame 的索引)

        Returns:
            分析结果字典
        """
        farm = self.farms.iloc[farm_id]

        # 基本信息
        result = {
            'farm_id': farm_id,
            'typology': farm.get('typology', 'unknown'),
            'cluster': farm.get('cluster_label', 'Unknown'),
            'phase': int(farm.get('phase', 4)),
            'phase_label': farm.get('phase_label', 'Phase 4'),
            'cluster_ratio': float(farm.get('cluster_ratio', 0)),

            # 面积计算
            'area_sqm': float(farm.geometry.area),
            'centroid_lat': float(farm.geometry.centroid.y),
            'centroid_lon': float(farm.geometry.centroid.x),

            # 连接的 POI
            'connected_pois': {
                'food': [],
                'social': [],
                'cultural': []
            },

            # 餐厅分析
            'restaurants': [],

            # 物种数据
            'nearby_species': [],
            'species_count': 0,
            'current_shannon_index': 0.0,

            # 推荐物种
            'recommended_species': [],
            'projected_shannon_index': 0.0,
            'biodiversity_impact': 0.0,

            # 种植潜力
            'planting_capacity': {}
        }

        # 获取 cluster 策略
        strategy = self.get_cluster_strategy(result['cluster'])

        # 分析连接的 POI
        result['connected_pois'] = self._analyze_connected_pois(farm_id, strategy)

        # 分析餐厅
        result['restaurants'] = self._analyze_restaurants(farm_id, result['connected_pois']['food'])

        # 分析周边物种
        species_analysis = self._analyze_nearby_species(farm.geometry)
        result['nearby_species'] = species_analysis['species_list']
        result['species_count'] = species_analysis['unique_count']
        result['current_shannon_index'] = species_analysis['shannon_index']

        # 生成物种推荐
        recommendations = self._generate_species_recommendations(
            species_analysis['species_list'],
            result['area_sqm']
        )
        result['recommended_species'] = recommendations['species']
        result['projected_shannon_index'] = recommendations['projected_shannon']
        result['biodiversity_impact'] = recommendations['impact']

        # 计算种植潜力
        result['planting_capacity'] = self._calculate_planting_capacity(result['area_sqm'])

        return result

    def _analyze_connected_pois(self, farm_id: int, strategy: Dict) -> Dict:
        """分析连接的 POI"""
        connected = {'food': [], 'social': [], 'cultural': []}

        # 获取该 farm 的连接线
        farm_connections = self.connections[self.connections['farm_id'] == farm_id]

        for poi_type in ['food', 'social', 'cultural']:
            type_connections = farm_connections[farm_connections['poi_type'] == poi_type]

            for _, conn in type_connections.iterrows():
                # 获取 POI 的末端坐标
                coords = list(conn.geometry.coords)
                if len(coords) >= 2:
                    poi_point = Point(coords[-1])  # POI 在线的末端

                    # 根据类型查找对应的 POI
                    if poi_type == 'food':
                        poi_gdf = self.food_poi
                    elif poi_type == 'social':
                        poi_gdf = self.social_poi
                    else:
                        poi_gdf = self.cultural_poi

                    # 查找最近的 POI（距离 < 10米）
                    distances = poi_gdf.geometry.distance(poi_point)
                    nearest_idx = distances[distances < 10].index

                    if len(nearest_idx) > 0:
                        poi = poi_gdf.iloc[nearest_idx[0]]
                        poi_info = {
                            'distance': float(conn['distance']),
                            'name': poi.get('name', 'Unknown') if poi_type == 'food' else 'N/A'
                        }

                        if poi_type == 'food':
                            poi_info['subcategory'] = poi.get('subcategor', 'unknown')
                            # Convert to WGS84 for lat/lon (Google API needs geographic coordinates)
                            poi_wgs84 = poi_gdf.iloc[[nearest_idx[0]]].to_crs(CRS_GEOGRAPHIC).iloc[0]
                            poi_info['lat'] = float(poi_wgs84.geometry.y)
                            poi_info['lon'] = float(poi_wgs84.geometry.x)

                        connected[poi_type].append(poi_info)

        # 去重
        for poi_type in connected:
            seen = set()
            unique = []
            for poi in connected[poi_type]:
                key = poi.get('name', poi.get('lat', str(poi)))
                if key not in seen:
                    seen.add(key)
                    unique.append(poi)
            connected[poi_type] = unique

        return connected

    def _analyze_restaurants(self, farm_id: int, food_pois: List[Dict]) -> List[Dict]:
        """分析餐厅（包括照片和VLM分析）- 分析所有已连接的餐厅"""
        restaurants = []

        # 按距离排序
        sorted_pois = sorted(food_pois, key=lambda x: x.get('distance', float('inf')))

        print(f"    Analyzing {len(sorted_pois)} connected restaurants...")

        for poi in sorted_pois:
            restaurant_info = {
                'name': poi.get('name', 'Unknown'),
                'subcategory': poi.get('subcategory', 'unknown'),
                'distance': poi.get('distance', 0),
                'lat': poi.get('lat'),
                'lon': poi.get('lon'),
                'details': None,
                'potential_ingredients': [],
                'vlm_analysis': None
            }

            # 如果启用 VLM API，进行完整照片分析（分析所有可用照片）
            if self.use_vlm_api and self.photo_analyzer and poi.get('lat') and poi.get('lon'):
                try:
                    print(f"      [{len(restaurants)+1}/{len(sorted_pois)}] {poi['name']} ({poi['lat']:.4f}, {poi['lon']:.4f})")
                    vlm_result = self.photo_analyzer.analyze_restaurant(
                        name=poi['name'],
                        lat=poi['lat'],
                        lon=poi['lon'],
                        max_photos=10,  # Analyze up to 10 photos per restaurant
                        farm_id=farm_id
                    )
                    restaurant_info['vlm_analysis'] = {
                        'place_id': vlm_result.get('place_id'),
                        'photos_analyzed': vlm_result.get('photos_analyzed'),
                        'cuisine_types': vlm_result.get('cuisine_types', []),
                        'ingredients': vlm_result.get('aggregated_ingredients', []),
                        'farmable_ingredients': vlm_result.get('farmable_ingredients', {}),
                        'growing_recommendations': vlm_result.get('growing_recommendations', {}),
                        'photo_files': vlm_result.get('photo_files', []),
                        'image_dir': vlm_result.get('image_dir')
                    }
                    restaurant_info['potential_ingredients'] = vlm_result.get('aggregated_ingredients', [])
                except Exception as e:
                    print(f"      VLM analysis failed: {e}")

            # 如果只启用 Google API（没有VLM），获取基本信息
            elif self.use_google_api and self.places_client and poi.get('lat') and poi.get('lon'):
                details = self.places_client.get_restaurant_info(
                    poi['name'],
                    poi['lat'],
                    poi['lon']
                )
                restaurant_info['details'] = details
                restaurant_info['potential_ingredients'] = self.places_client.extract_potential_ingredients(
                    details,
                    poi.get('subcategory', 'restaurant')
                )

            restaurants.append(restaurant_info)

        return restaurants

    def _analyze_nearby_species(self, farm_geometry) -> Dict:
        """分析 farm 周边的物种"""
        # 创建缓冲区
        buffer = farm_geometry.buffer(SPECIES_BUFFER)

        # 找到缓冲区内的物种
        nearby = self.plantae[self.plantae.geometry.within(buffer)]

        # 统计物种
        species_counts = Counter()
        species_list = []

        for _, obs in nearby.iterrows():
            taxon_name = obs.get('taxon_name', 'Unknown')
            if taxon_name and taxon_name != 'Unknown':
                species_counts[taxon_name] += 1

                # 添加到列表（去重）
                species_info = {
                    'taxon_name': taxon_name,
                    'common_name': obs.get('common_name'),
                    'count': species_counts[taxon_name]
                }

                # 检查是否已存在
                existing = next((s for s in species_list if s['taxon_name'] == taxon_name), None)
                if existing:
                    existing['count'] = species_counts[taxon_name]
                else:
                    species_list.append(species_info)

        # 计算 Shannon 多样性指数
        shannon = calculate_shannon_diversity(dict(species_counts))

        return {
            'species_list': species_list,
            'unique_count': len(species_counts),
            'total_observations': sum(species_counts.values()),
            'shannon_index': shannon
        }

    def _generate_species_recommendations(self, existing_species: List[Dict],
                                          area_sqm: float) -> Dict:
        """生成物种推荐"""
        # 提取物种名称
        species_names = [s['taxon_name'] for s in existing_species]

        # 如果启用 LLM API，进行分类
        if self.use_llm_api and self.species_classifier:
            classifications = []
            for species in existing_species[:20]:  # 限制数量
                result = self.species_classifier.classify_species(
                    species['taxon_name'],
                    species.get('common_name')
                )
                classifications.append(result)

            # 获取推荐
            recommended = self.species_classifier.get_recommended_species(
                classifications,
                min_area_sqm=area_sqm * 0.1
            )
        else:
            # 使用简单的启发式规则
            recommended = self._simple_species_recommendation(existing_species, area_sqm)

        # 计算预期生物多样性影响
        current_shannon = calculate_shannon_diversity(
            {s['taxon_name']: s['count'] for s in existing_species}
        )

        # 假设添加推荐物种后的多样性
        projected_species = dict(species_counts for species_counts in
                                 [(s['taxon_name'], 1) for s in recommended[:10]])
        projected_species.update({s['taxon_name']: s['count'] for s in existing_species})

        projected_shannon = calculate_shannon_diversity(projected_species)
        impact = projected_shannon - current_shannon

        return {
            'species': recommended,
            'projected_shannon': projected_shannon,
            'impact': impact
        }

    def _simple_species_recommendation(self, existing_species: List[Dict],
                                        area_sqm: float) -> List[Dict]:
        """简单的物种推荐（不使用 API）"""
        # 常见可食用本土植物
        common_edible = [
            {'taxon_name': 'Centella asiatica', 'common_name': 'Pegaga', 'edible_type': 'leafy'},
            {'taxon_name': 'Murraya koenigii', 'common_name': 'Curry Leaf', 'edible_type': 'herb'},
            {'taxon_name': 'Ocimum tenuiflorum', 'common_name': 'Holy Basil', 'edible_type': 'herb'},
            {'taxon_name': 'Cymbopogon citratus', 'common_name': 'Lemongrass', 'edible_type': 'herb'},
            {'taxon_name': 'Persicaria odorata', 'common_name': 'Laksa Leaf', 'edible_type': 'herb'},
            {'taxon_name': 'Ipomoea aquatica', 'common_name': 'Kangkong', 'edible_type': 'leafy'},
            {'taxon_name': 'Moringa oleifera', 'common_name': 'Drumstick', 'edible_type': 'leafy'},
            {'taxon_name': 'Hibiscus sabdariffa', 'common_name': 'Roselle', 'edible_type': 'fruit'},
            {'taxon_name': 'Sauropus androgynus', 'common_name': 'Katuk', 'edible_type': 'leafy'},
            {'taxon_name': 'Gynura procumbens', 'common_name': 'Longevity Spinach', 'edible_type': 'leafy'},
        ]

        # 过滤已存在的物种
        existing_names = {s['taxon_name'] for s in existing_species}
        recommended = []

        for species in common_edible:
            if species['taxon_name'] not in existing_names:
                recommended.append({
                    'taxon_name': species['taxon_name'],
                    'common_name': species['common_name'],
                    'is_indigenous': True,
                    'is_edible': True,
                    'edible_type': species['edible_type'],
                    'priority': 'high',
                    'min_area_sqm': area_sqm * 0.05,
                    'confidence': 'high'
                })

        return recommended[:5]  # 返回前 5 个

    def _calculate_planting_capacity(self, area_sqm: float) -> Dict:
        """计算种植潜力"""
        return {
            'leafy': estimate_planting_capacity(area_sqm, 'leafy'),
            'herb': estimate_planting_capacity(area_sqm, 'herb'),
            'root': estimate_planting_capacity(area_sqm, 'root'),
            'fruit': estimate_planting_capacity(area_sqm, 'fruit'),
            'legume': estimate_planting_capacity(area_sqm, 'legume'),
            'total_area_sqm': area_sqm,
            'usable_area_sqm': area_sqm * 0.6
        }

    def run_analysis(self, phase_filter: Optional[int] = None) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        运行批量分析

        Args:
            phase_filter: 只分析指定 Phase 的 farms (None 表示全部)

        Returns:
            (摘要 DataFrame, 详细报告列表)
        """
        # 筛选 farms
        if phase_filter:
            farm_ids = self.farms[self.farms['phase'] == phase_filter].index.tolist()
        else:
            farm_ids = self.farms.index.tolist()

        print(f"\nAnalyzing {len(farm_ids)} farms...")

        all_reports = []
        summary_data = []

        for i, farm_id in enumerate(farm_ids):
            print(f"  Processing farm {farm_id} ({i+1}/{len(farm_ids)})")

            report = self.analyze_farm(farm_id)
            all_reports.append(report)

            # 保存单独报告
            report_path = OUTPUT_DIR / f"farm_{farm_id}.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)

            # 添加摘要
            summary_data.append({
                'farm_id': farm_id,
                'typology': report['typology'],
                'phase': report['phase'],
                'cluster': report['cluster'],
                'area_sqm': report['area_sqm'],
                'food_connections': len(report['connected_pois']['food']),
                'social_connections': len(report['connected_pois']['social']),
                'cultural_connections': len(report['connected_pois']['cultural']),
                'restaurant_count': len(report['restaurants']),
                'species_count': report['species_count'],
                'current_shannon': report['current_shannon_index'],
                'projected_shannon': report['projected_shannon_index'],
                'biodiversity_impact': report['biodiversity_impact'],
                'recommended_species_count': len(report['recommended_species']),
                'leafy_capacity': report['planting_capacity']['leafy'],
                'herb_capacity': report['planting_capacity']['herb']
            })

        # 创建摘要 DataFrame
        summary_df = pd.DataFrame(summary_data)

        # 保存摘要 CSV
        summary_df.to_csv(OUTPUT_DIR / 'farm_micro_analysis.csv', index=False)
        print(f"\nSaved summary to {OUTPUT_DIR / 'farm_micro_analysis.csv'}")

        # 保存完整报告
        with open(OUTPUT_DIR / 'all_farm_reports.json', 'w', encoding='utf-8') as f:
            json.dump(all_reports, f, ensure_ascii=False, indent=2)
        print(f"Saved full reports to {OUTPUT_DIR / 'all_farm_reports.json'}")

        # 打印 API 统计
        if self.use_google_api and self.places_client:
            print(f"\nGoogle Places API Stats: {self.places_client.get_stats()}")
        if self.use_llm_api and self.species_classifier:
            print(f"LLM API Stats: {self.species_classifier.get_stats()}")

        return summary_df, all_reports


def enrich_connections():
    """
    增强 network connections 数据
    将 POI 详细信息添加到连接线属性中
    """
    print("\nEnriching network connections...")

    # 加载数据
    connections = gpd.read_file('network_visualization/network_connections_400m.geojson')
    connections = connections.to_crs(CRS_PROJECTED)

    food_poi = gpd.read_file('json/food.geojson')
    food_poi = food_poi.to_crs(CRS_PROJECTED)

    social_poi = gpd.read_file('json/social_dim.geojson')
    social_poi = social_poi.to_crs(CRS_PROJECTED)

    cultural_poi = gpd.read_file('json/cultural_dim.geojson')
    cultural_poi = cultural_poi.to_crs(CRS_PROJECTED)

    # 为每条连接线添加 POI 信息
    enriched_features = []

    for idx, conn in connections.iterrows():
        props = dict(conn)
        coords = list(conn.geometry.coords)

        if len(coords) >= 2:
            poi_point = Point(coords[-1])  # POI 在线的末端

            # 根据 POI 类型查找详细信息
            poi_type = conn['poi_type']
            if poi_type == 'food':
                poi_gdf = food_poi
            elif poi_type == 'social':
                poi_gdf = social_poi
            else:
                poi_gdf = cultural_poi

            # 查找最近的 POI
            distances = poi_gdf.geometry.distance(poi_point)
            nearest_idx = distances.idxmin()

            if distances[nearest_idx] < 10:  # 10米阈值
                poi = poi_gdf.iloc[nearest_idx]

                # 添加 POI 属性
                props['poi_name'] = poi.get('name', '') if poi_type == 'food' else ''
                props['poi_lat'] = float(poi.geometry.y)
                props['poi_lon'] = float(poi.geometry.x)

                if poi_type == 'food':
                    props['poi_subcategory'] = poi.get('subcategor', '')

        enriched_features.append({
            'type': 'Feature',
            'properties': {
                'farm_id': props.get('farm_id'),
                'poi_type': props.get('poi_type'),
                'distance': props.get('distance'),
                'cluster': props.get('cluster'),
                'phase': props.get('phase'),
                'poi_name': props.get('poi_name', ''),
                'poi_lat': props.get('poi_lat'),
                'poi_lon': props.get('poi_lon'),
                'poi_subcategory': props.get('poi_subcategory', '')
            },
            'geometry': conn.geometry.__geo_interface__
        })

    # 保存增强后的数据
    enriched_geojson = {
        'type': 'FeatureCollection',
        'features': enriched_features
    }

    output_path = 'network_visualization/network_connections_400m_enriched.geojson'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_geojson, f, ensure_ascii=False, indent=2)

    print(f"Saved enriched connections to {output_path}")

    return output_path


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='Urban Agroecology Farm Micro-Analysis')
    parser.add_argument('--phase', type=int, default=None,
                        help='Only analyze farms in this phase (1-4)')
    parser.add_argument('--use-google-api', action='store_true',
                        help='Enable Google Places API for restaurant details')
    parser.add_argument('--use-llm-api', action='store_true',
                        help='Enable LLM API for species classification')
    parser.add_argument('--use-vlm-api', action='store_true',
                        help='Enable VLM API for restaurant photo analysis')
    parser.add_argument('--quick-test', action='store_true',
                        help='Quick test mode: 1 restaurant per farm, 2 photos max (with 5-hour timer limit)')
    parser.add_argument('--enrich-connections', action='store_true',
                        help='Only enrich connection lines with POI details')

    args = parser.parse_args()

    if args.enrich_connections:
        enrich_connections()
        return

    # 运行分析
    analyzer = FarmMicroAnalyzer(
        use_google_api=args.use_google_api,
        use_llm_api=args.use_llm_api,
        use_vlm_api=args.use_vlm_api
    )

    summary_df, reports = analyzer.run_analysis(phase_filter=args.phase)

    # 打印摘要统计
    print("\n" + "="*60)
    print("Analysis Summary")
    print("="*60)
    print(f"Total farms analyzed: {len(summary_df)}")
    print(f"Total area: {summary_df['area_sqm'].sum():.1f} sqm")
    print(f"Average Shannon Index: {summary_df['current_shannon'].mean():.3f}")
    print(f"Average projected Shannon: {summary_df['projected_shannon'].mean():.3f}")
    print(f"Average biodiversity impact: {summary_df['biodiversity_impact'].mean():.3f}")

    if args.phase:
        print(f"\nPhase {args.phase} statistics:")
        print(f"  Farms: {len(summary_df)}")
        print(f"  Food connections: {summary_df['food_connections'].sum()}")
        print(f"  Restaurant count: {summary_df['restaurant_count'].sum()}")


if __name__ == "__main__":
    main()
