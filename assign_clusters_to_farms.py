"""
将 4 种 farm typology 分配到 clusters
如果一个 site 跨越多个 cluster，选择面积占比最大的
"""

import geopandas as gpd
import pandas as pd
from pathlib import Path

FARM_DIR = Path("farm")
CLUSTER_PATH = "data/fishnet_clusters.shp"
OUTPUT_DIR = Path("farm_with_clusters")
OUTPUT_DIR.mkdir(exist_ok=True)

TYPOLOGIES = ['podium', 'rooftops', 'streetscapes', 'green_spaces']

# Shapefile 列名会被截断
CLUSTER_LABEL_COL = 'cluster_la'


def assign_clusters(sites: gpd.GeoDataFrame, clusters: gpd.GeoDataFrame, typology_name: str) -> gpd.GeoDataFrame:
    """将 sites 分配到 clusters"""

    # 确保有唯一 ID
    sites = sites.copy()
    sites['_site_id'] = range(len(sites))

    # 计算每个 site 的面积
    sites['_site_area'] = sites.geometry.area

    # Spatial overlay: intersect
    overlay = gpd.overlay(sites, clusters, how='intersection')

    if len(overlay) == 0:
        print(f"  Warning: No overlap with clusters!")
        return None

    # 计算重叠面积和比例
    overlay['_overlap_area'] = overlay.geometry.area
    overlay['_overlap_ratio'] = overlay['_overlap_area'] / overlay['_site_area']

    # 选择每个 site 占比最大的 cluster
    idx_max = overlay.groupby('_site_id')['_overlap_ratio'].idxmax()
    assigned = overlay.loc[idx_max].copy()

    # 清理临时列
    result = sites.merge(
        assigned[['_site_id', 'cluster', CLUSTER_LABEL_COL, '_overlap_ratio']],
        on='_site_id',
        how='left'
    )
    result = result.rename(columns={'_overlap_ratio': 'cluster_ratio', CLUSTER_LABEL_COL: 'cluster_label'})
    result = result.drop(columns=['_site_id', '_site_area'])
    result['typology'] = typology_name

    return result


def main():
    print("=" * 60)
    print("Farm Typology Cluster Assignment")
    print("=" * 60)

    # 读取 clusters
    clusters = gpd.read_file(CLUSTER_PATH)
    print(f"\nClusters: {len(clusters)} grids, CRS: {clusters.crs}")

    all_results = []
    summary_data = []

    for typology in TYPOLOGIES:
        print(f"\n[{typology}]")

        # 读取 farm sites
        sites = gpd.read_file(FARM_DIR / f"{typology}.geojson")
        print(f"  Sites: {len(sites)}, CRS: {sites.crs}")

        # 转换 CRS
        sites = sites.to_crs(clusters.crs)

        # 分配 cluster
        result = assign_clusters(sites, clusters, typology)

        if result is not None:
            # 统计
            cluster_counts = result.groupby('cluster').size()
            print(f"  Assigned to clusters:")
            for c, count in cluster_counts.items():
                label = result[result['cluster'] == c]['cluster_label'].iloc[0]
                print(f"    Cluster {c} ({label}): {count} sites")
                summary_data.append({
                    'typology': typology,
                    'cluster': c,
                    'cluster_label': label,
                    'count': count
                })

            # 保存单独文件
            output_path = OUTPUT_DIR / f"{typology}_clustered.geojson"
            result.to_file(output_path, driver='GeoJSON')
            print(f"  Saved: {output_path}")

            all_results.append(result)

    # 合并所有 typology
    if all_results:
        combined = gpd.GeoDataFrame(pd.concat(all_results, ignore_index=True), crs=clusters.crs)
        combined.to_file(OUTPUT_DIR / "all_farms_clustered.geojson", driver='GeoJSON')
        print(f"\nSaved combined: {OUTPUT_DIR / 'all_farms_clustered.geojson'}")

    # 汇总表
    print("\n" + "=" * 60)
    print("Summary by Typology and Cluster")
    print("=" * 60)
    summary_df = pd.DataFrame(summary_data)
    pivot = summary_df.pivot_table(index='typology', columns='cluster_label', values='count', fill_value=0, aggfunc='sum')
    print(pivot.to_string())

    # 保存汇总
    summary_df.to_csv(OUTPUT_DIR / "cluster_assignment_summary.csv", index=False)
    print(f"\nSaved summary: {OUTPUT_DIR / 'cluster_assignment_summary.csv'}")


if __name__ == "__main__":
    main()
