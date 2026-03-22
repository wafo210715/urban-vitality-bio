"""
将 vitality 分类到 4 个 phases（基于标准差）
然后分配到 farm sites
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

VITALITY_PATH = "json/vitality_results.geojson"
FARM_PATH = "farm_with_clusters/all_farms_clustered.geojson"
OUTPUT_DIR = Path("farm_with_clusters")

def classify_vitality_std(value, mean, std):
    """基于标准差分类 vitality - REVERSED: 高活力 = 优先干预"""
    if value >= mean + std:
        return 1  # Urgent - highest vitality, engage first
    elif value >= mean:
        return 2  # High Priority
    elif value >= mean - std:
        return 3  # Medium Priority
    else:
        return 4  # Low Priority - lowest vitality, later phase


def phase_label(phase):
    """Phase 标签"""
    labels = {
        1: "Phase 1 - Aggressive",
        2: "Phase 2 - High Priority",
        3: "Phase 3 - Medium Priority",
        4: "Phase 4 - Later Phase"
    }
    return labels.get(phase, f"Phase {phase}")


def main():
    print("=" * 60)
    print("Vitality-Based Phasing for Farm Sites")
    print("=" * 60)

    # 读取 vitality 数据
    vitality_gdf = gpd.read_file(VITALITY_PATH)
    print(f"\nVitality grids: {len(vitality_gdf)}")

    # 计算 mean 和 std
    mean = vitality_gdf['vitality'].mean()
    std = vitality_gdf['vitality'].std()

    print(f"Vitality Mean: {mean:.4f}")
    print(f"Vitality Std:  {std:.4f}")
    print()
    print("Classification thresholds:")
    print(f"  Phase 1 (Urgent):         vitality < {mean - std:.4f}")
    print(f"  Phase 2 (High Priority):  {mean - std:.4f} <= vitality < {mean:.4f}")
    print(f"  Phase 3 (Medium Priority): {mean:.4f} <= vitality < {mean + std:.4f}")
    print(f"  Phase 4 (Stable):         vitality >= {mean + std:.4f}")

    # 分类 vitality grids
    vitality_gdf['phase'] = vitality_gdf['vitality'].apply(
        lambda x: classify_vitality_std(x, mean, std)
    )
    vitality_gdf['phase_label'] = vitality_gdf['phase'].apply(phase_label)

    # 统计每个 phase 的网格数
    print("\nVitality grids per phase:")
    phase_counts = vitality_gdf.groupby('phase').size()
    for p, count in phase_counts.items():
        print(f"  {phase_label(p)}: {count} grids ({count/len(vitality_gdf)*100:.1f}%)")

    # 读取 farm sites
    farms = gpd.read_file(FARM_PATH)
    print(f"\nFarm sites: {len(farms)}")

    # 确保 CRS 一致
    if farms.crs != vitality_gdf.crs:
        farms = farms.to_crs(vitality_gdf.crs)

    # Spatial join: farm sites 与 vitality grids
    print("\nAssigning phases to farm sites...")

    # 转换到投影坐标系进行面积计算
    farms_proj = farms.to_crs('EPSG:32648')
    vitality_proj = vitality_gdf.to_crs('EPSG:32648')

    # 添加唯一 ID
    farms['_site_id'] = range(len(farms))
    farms_proj['_site_id'] = range(len(farms_proj))
    farms_proj['_site_area'] = farms_proj.geometry.area

    # Intersection
    overlay = gpd.overlay(
        farms_proj[['_site_id', '_site_area', 'typology', 'cluster', 'cluster_label', 'geometry']],
        vitality_proj[['phase', 'phase_label', 'geometry']],
        how='intersection'
    )

    # 计算重叠面积
    overlay['_overlap_area'] = overlay.geometry.area
    overlay['_overlap_ratio'] = overlay['_overlap_area'] / overlay['_site_area']

    # 选择每个 site 占比最大的 phase
    idx_max = overlay.groupby('_site_id')['_overlap_ratio'].idxmax()
    assigned = overlay.loc[idx_max].copy()

    # 合并回原始 farms
    result = farms.merge(
        assigned[['_site_id', 'phase', 'phase_label', '_overlap_ratio']],
        on='_site_id',
        how='left'
    )
    result = result.rename(columns={'_overlap_ratio': 'phase_ratio'})
    result = result.drop(columns=['_site_id'])

    # 统计
    print("\nFarm sites per phase:")
    phase_farm_counts = result.groupby('phase').size()
    for p in sorted(result['phase'].dropna().unique()):
        count = phase_farm_counts.get(p, 0)
        print(f"  {phase_label(int(p))}: {count} sites")

    # 按 typology 和 phase 统计
    print("\nFarm sites by Typology and Phase:")
    cross_tab = pd.crosstab(result['typology'], result['phase'])
    print(cross_tab.to_string())

    # 保存结果
    output_path = OUTPUT_DIR / "all_farm_phases.geojson"
    result.to_file(output_path, driver='GeoJSON')
    print(f"\nSaved: {output_path}")

    # 也保存 shapefile
    result.to_file(OUTPUT_DIR / "all_farm_phases.shp")
    print(f"Saved: {OUTPUT_DIR / 'all_farm_phases.shp'}")

    # 保存汇总表
    cross_tab.to_csv(OUTPUT_DIR / "farm_phases_summary.csv")
    print(f"Saved: {OUTPUT_DIR / 'farm_phases_summary.csv'}")


if __name__ == "__main__":
    main()
