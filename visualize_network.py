"""
Urban Agroecology Network Visualization
按 Phase 顺序绘制网络连接（只在 fishnet 范围内）
区分 cluster 类型：只有 Low-Activity 不连接 POI

生成两种距离：5分钟(400m) 和 10分钟(800m)
"""

import geopandas as gpd
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
from shapely.geometry import LineString
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

# ============ 配置 ============
WALKING_DISTANCES = [400, 800]  # 5分钟和10分钟
CRS_PROJECTED = 'EPSG:32648'
CRS_GEOGRAPHIC = 'EPSG:4326'
OUTPUT_DIR = Path('network_visualization')
OUTPUT_DIR.mkdir(exist_ok=True)

# ============ 读取数据 ============
print("Loading data...")
farms = gpd.read_file('farm_with_clusters/all_farm_phases.geojson')
food_poi = gpd.read_file('json/food.geojson')
cultural_poi = gpd.read_file('json/cultural_dim.geojson')
social_poi = gpd.read_file('json/social_dim.geojson')
fishnet = gpd.read_file('data/fishnet/fishnet.shp')

# 转换 CRS
farms = farms.to_crs(CRS_PROJECTED)
food_poi = food_poi.to_crs(CRS_PROJECTED)
cultural_poi = cultural_poi.to_crs(CRS_PROJECTED)
social_poi = social_poi.to_crs(CRS_PROJECTED)
fishnet_proj = fishnet.to_crs(CRS_PROJECTED)

# 获取 fishnet 边界
fishnet_polygon = fishnet_proj.unary_union
print(f"Fishnet bounds: {fishnet_proj.total_bounds}")

# 过滤 POI 只保留在 fishnet 范围内的
print("Filtering POIs within fishnet boundary...")
food_poi = food_poi[food_poi.geometry.within(fishnet_polygon)]
cultural_poi = cultural_poi[cultural_poi.geometry.within(fishnet_polygon)]
social_poi = social_poi[social_poi.geometry.within(fishnet_polygon)]

print(f"Farms: {len(farms)}")
print(f"Food POI (filtered): {len(food_poi)}")
print(f"Cultural POI (filtered): {len(cultural_poi)}")
print(f"Social POI (filtered): {len(social_poi)}")

# ============ 辅助函数 ============
def find_nearby_pois(farm, poi_gdf, max_distance):
    """找到 farm 周围指定距离内的 POI"""
    distances = poi_gdf.geometry.distance(farm.geometry.centroid)
    nearby = poi_gdf[distances <= max_distance].copy()
    nearby['distance'] = distances[distances <= max_distance]
    return nearby

def get_cluster_strategy(cluster_label):
    """根据 cluster 类型返回连接策略"""
    strategies = {
        'Cultural-Economic': {
            'connect_to': ['food', 'social'],
            'emphasis': 'Social Activities',
            'color': '#2ca02c'
        },
        'Economic-Only': {
            'connect_to': ['food', 'social', 'cultural'],
            'emphasis': 'Social + Cultural',
            'color': '#9467bd'
        },
        'Low-Activity': {
            'connect_to': [],  # 不连接 POI，专注生物多样性
            'emphasis': 'Biodiversity',
            'color': '#8c564b'
        },
        'Socio-Economic': {
            'connect_to': ['food', 'cultural'],
            'emphasis': 'Cultural Activities',
            'color': '#1f77b4'
        }
    }
    return strategies.get(cluster_label, strategies['Low-Activity'])

# 颜色配置
poi_colors = {'food': '#ff7f0e', 'social': '#2ca02c', 'cultural': '#1f77b4'}
phase_colors = {
    1: '#e41a1c',  # Aggressive - Red
    2: '#ff7f00',  # High Priority - Orange
    3: '#984ea3',  # Medium Priority - Purple
    4: '#4daf4a'   # Later Phase - Green
}
cluster_colors = {
    'Cultural-Economic': '#2ca02c',
    'Economic-Only': '#9467bd',
    'Low-Activity': '#8c564b',
    'Socio-Economic': '#1f77b4'
}
phase_labels = {
    1: 'Phase 1 - Aggressive',
    2: 'Phase 2 - High Priority',
    3: 'Phase 3 - Medium Priority',
    4: 'Phase 4 - Later Phase'
}

# ============ 主处理逻辑（按距离循环） ============
for WALKING_DISTANCE in WALKING_DISTANCES:
    print(f"\n{'='*60}")
    print(f"Processing with {WALKING_DISTANCE}m walking distance")
    print(f"{'='*60}")

    all_connections = []
    farm_stats = []

    for idx, farm in farms.iterrows():
        cluster_label = farm.get('cluster_label', 'Low-Activity')
        phase = farm.get('phase', 4)
        strategy = get_cluster_strategy(cluster_label)

        farm_stat = {
            'farm_id': int(farm['FID']) if pd.notna(farm.get('FID')) else idx,
            'typology': farm.get('typology', 'unknown'),
            'phase': phase,
            'cluster': cluster_label,
            'emphasis': strategy['emphasis'],
            'food_connections': 0,
            'social_connections': 0,
            'cultural_connections': 0
        }

        # 根据 cluster 策略连接 POI（Low-Activity 不连接）
        if 'food' in strategy['connect_to']:
            nearby_food = find_nearby_pois(farm, food_poi, WALKING_DISTANCE)
            farm_stat['food_connections'] = len(nearby_food)
            for _, poi in nearby_food.iterrows():
                line = LineString([farm.geometry.centroid, poi.geometry])
                all_connections.append({
                    'farm_id': int(farm['FID']) if pd.notna(farm.get('FID')) else idx,
                    'geometry': line,
                    'poi_type': 'food',
                    'distance': poi.get('distance', 0),
                    'cluster': cluster_label,
                    'phase': phase
                })

        if 'social' in strategy['connect_to']:
            nearby_social = find_nearby_pois(farm, social_poi, WALKING_DISTANCE)
            farm_stat['social_connections'] = len(nearby_social)
            for _, poi in nearby_social.iterrows():
                line = LineString([farm.geometry.centroid, poi.geometry])
                all_connections.append({
                    'farm_id': int(farm['FID']) if pd.notna(farm.get('FID')) else idx,
                    'geometry': line,
                    'poi_type': 'social',
                    'distance': poi.get('distance', 0),
                    'cluster': cluster_label,
                    'phase': phase
                })

        if 'cultural' in strategy['connect_to']:
            nearby_cultural = find_nearby_pois(farm, cultural_poi, WALKING_DISTANCE)
            farm_stat['cultural_connections'] = len(nearby_cultural)
            for _, poi in nearby_cultural.iterrows():
                line = LineString([farm.geometry.centroid, poi.geometry])
                all_connections.append({
                    'farm_id': int(farm['FID']) if pd.notna(farm.get('FID')) else idx,
                    'geometry': line,
                    'poi_type': 'cultural',
                    'distance': poi.get('distance', 0),
                    'cluster': cluster_label,
                    'phase': phase
                })

        farm_stats.append(farm_stat)

    # ============ 保存结果 ============
    dist_label = f"{WALKING_DISTANCE}m"

    # 连接线 GeoDataFrame
    if all_connections:
        connections_gdf = gpd.GeoDataFrame(all_connections, crs=CRS_PROJECTED)
        connections_gdf_geo = connections_gdf.to_crs(CRS_GEOGRAPHIC)
        connections_gdf_geo.to_file(OUTPUT_DIR / f'network_connections_{dist_label}.geojson', driver='GeoJSON')
        connections_gdf_geo.to_file(OUTPUT_DIR / f'network_connections_{dist_label}.shp')
        print(f"Saved: {len(connections_gdf)} connection lines")

    # Farm 统计
    stats_df = pd.DataFrame(farm_stats)
    stats_df.to_csv(OUTPUT_DIR / f'farm_network_stats_{dist_label}.csv', index=False)

    # ============ 可视化 ============
    print(f"Creating visualization for {dist_label}...")

    # ========== 按 Phase 分组绘制 ==========
    fig, axes = plt.subplots(2, 2, figsize=(20, 16))
    axes = axes.flatten()

    for i, phase in enumerate([1, 2, 3, 4]):
        ax = axes[i]

        # 绘制 fishnet 边界
        fishnet_proj.plot(ax=ax, facecolor='none', edgecolor='lightgray', linewidth=0.3, alpha=0.5)

        # Phase 对应的 farms
        phase_farms = farms[farms['phase'] == phase]

        if len(phase_farms) == 0:
            ax.set_title(f'{phase_labels[phase]}\nNo farms', fontsize=12)
            ax.set_axis_off()
            continue

        # 绘制该 phase 的连接线（按 cluster 策略）
        phase_connections = [c for c in all_connections if c['phase'] == phase]
        for conn in phase_connections:
            xs, ys = conn['geometry'].xy
            ax.plot(xs, ys, color=poi_colors.get(conn['poi_type'], 'gray'),
                   alpha=0.4, linewidth=0.5)

        # 按 cluster 类型绘制 farm sites（区分颜色）
        for cluster_name in phase_farms['cluster_label'].unique():
            cluster_farms = phase_farms[phase_farms['cluster_label'] == cluster_name]
            cluster_farms.plot(ax=ax, color=cluster_colors.get(cluster_name, 'gray'),
                              alpha=0.8, edgecolor='white', linewidth=0.5)

        # 绘制 POI
        food_poi.plot(ax=ax, color=poi_colors['food'], markersize=8, alpha=0.5)
        social_poi.plot(ax=ax, color=poi_colors['social'], markersize=12, marker='s', alpha=0.6)
        cultural_poi.plot(ax=ax, color=poi_colors['cultural'], markersize=12, marker='^', alpha=0.6)

        # 统计
        n_connections = len(phase_connections)
        n_farms = len(phase_farms)
        n_low_activity = len(phase_farms[phase_farms['cluster_label'] == 'Low-Activity'])
        n_with_poi = n_farms - n_low_activity

        ax.set_title(f'{phase_labels[phase]}\n{n_farms} farms ({n_with_poi} with POI, {n_low_activity} biodiversity-only)\n{n_connections} connections',
                     fontsize=11)
        ax.set_axis_off()

    # 图例
    legend_elements = [
        Patch(facecolor=cluster_colors['Cultural-Economic'], label='Cultural-Economic (Food+Social)'),
        Patch(facecolor=cluster_colors['Economic-Only'], label='Economic-Only (Food+Social+Cultural)'),
        Patch(facecolor=cluster_colors['Socio-Economic'], label='Socio-Economic (Food+Cultural)'),
        Patch(facecolor=cluster_colors['Low-Activity'], label='Low-Activity (Biodiversity only)'),
        Line2D([0], [0], color=poi_colors['food'], linewidth=3, label='Food POI'),
        Line2D([0], [0], color=poi_colors['social'], linewidth=3, label='Social POI'),
        Line2D([0], [0], color=poi_colors['cultural'], linewidth=3, label='Cultural POI'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=9, bbox_to_anchor=(0.5, 0.01))

    plt.suptitle(f'Urban Agroecology Network by Phase\n{dist_label} Walking Distance | Cluster-based POI Connections', fontsize=16, fontweight='bold')
    plt.tight_layout(rect=[0, 0.06, 1, 0.95])
    plt.savefig(OUTPUT_DIR / f'network_by_phase_{dist_label}.png', dpi=150, bbox_inches='tight')
    print(f"Saved: network_by_phase_{dist_label}.png")

    # ========== 总览图 ==========
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))

    # 绘制 fishnet 边界
    fishnet_proj.plot(ax=ax, facecolor='none', edgecolor='lightgray', linewidth=0.3, alpha=0.5)

    # 按 phase 顺序绘制连接线 (Phase 1 最上层)
    for phase in [4, 3, 2, 1]:
        phase_connections = [c for c in all_connections if c['phase'] == phase]
        for conn in phase_connections:
            xs, ys = conn['geometry'].xy
            ax.plot(xs, ys, color=poi_colors.get(conn['poi_type'], 'gray'),
                   alpha=0.2, linewidth=0.3)

    # 按 cluster 类型绘制 farms
    for cluster_name in farms['cluster_label'].unique():
        cluster_farms = farms[farms['cluster_label'] == cluster_name]
        cluster_farms.plot(ax=ax, color=cluster_colors.get(cluster_name, 'gray'),
                          alpha=0.8, edgecolor='white', linewidth=0.5)

    # POI
    food_poi.plot(ax=ax, color=poi_colors['food'], markersize=5, alpha=0.4)
    social_poi.plot(ax=ax, color=poi_colors['social'], markersize=8, marker='s', alpha=0.5)
    cultural_poi.plot(ax=ax, color=poi_colors['cultural'], markersize=8, marker='^', alpha=0.5)

    # 图例
    legend_elements = [
        Patch(facecolor=cluster_colors['Cultural-Economic'], label='Cultural-Economic (Food+Social)'),
        Patch(facecolor=cluster_colors['Economic-Only'], label='Economic-Only (Food+Social+Cultural)'),
        Patch(facecolor=cluster_colors['Socio-Economic'], label='Socio-Economic (Food+Cultural)'),
        Patch(facecolor=cluster_colors['Low-Activity'], label='Low-Activity (Biodiversity only)'),
        Line2D([0], [0], color=poi_colors['food'], linewidth=3, label='Food POI'),
        Line2D([0], [0], color=poi_colors['social'], linewidth=3, label='Social POI'),
        Line2D([0], [0], color=poi_colors['cultural'], linewidth=3, label='Cultural POI'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', fontsize=9)

    ax.set_title(f'Urban Agroecology Network Overview\n{len(farms)} Farms | {len(all_connections)} Connections | {dist_label} Walking Distance',
                 fontsize=14, fontweight='bold')
    ax.set_axis_off()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'network_overview_{dist_label}.png', dpi=150, bbox_inches='tight')
    print(f"Saved: network_overview_{dist_label}.png")

    # ============ 统计摘要 ============
    print(f"\n--- Statistics for {dist_label} ---")
    for phase in [1, 2, 3, 4]:
        phase_stats = [s for s in farm_stats if s['phase'] == phase]
        if len(phase_stats) > 0:
            food_sum = sum(s['food_connections'] for s in phase_stats)
            social_sum = sum(s['social_connections'] for s in phase_stats)
            cultural_sum = sum(s['cultural_connections'] for s in phase_stats)
            print(f"  {phase_labels[phase]}: {len(phase_stats)} farms, {food_sum+social_sum+cultural_sum} connections")

print("\n" + "=" * 60)
print("Done! Output files:")
print("=" * 60)
for f in sorted(OUTPUT_DIR.glob('*')):
    print(f"  {f}")
