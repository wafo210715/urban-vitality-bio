"""
计算 Fishnet 网格的 Shannon Diversity Index
分别计算鸟类和植物
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("data")


def shannon_diversity(series: pd.Series) -> float:
    """
    计算 Shannon Diversity Index
    H' = -Σ(pi * ln(pi))
    """
    counts = series.value_counts()
    if len(counts) <= 1:
        return 0.0

    total = counts.sum()
    proportions = counts / total
    # 过滤掉 0 值避免 log(0)
    proportions = proportions[proportions > 0]
    return -np.sum(proportions * np.log(proportions))


def calculate_diversity_for_taxa(taxa: str, fishnet: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """计算指定类别的 diversity"""

    # 读取观测数据
    obs = gpd.read_file(OUTPUT_DIR / f"inat_{taxa.lower()}.geojson")
    print(f"\n[{taxa}] {len(obs)} observations")

    # 确保坐标系一致
    obs = obs.to_crs(fishnet.crs)

    # Spatial join: 将观测点分配到网格
    joined = gpd.sjoin(obs, fishnet[['grid_id', 'geometry']], how='left', predicate='within')
    print(f"  Points within fishnet: {joined['grid_id'].notna().sum()}")

    # 按 grid_id 分组计算 diversity
    diversity_results = joined.groupby('grid_id').agg(
        species_count=('taxon_name', 'count'),
        species_richness=('taxon_name', 'nunique'),
        shannon_diversity=('taxon_name', shannon_diversity)
    ).reset_index()

    print(f"  Grids with data: {len(diversity_results)}")
    print(f"  Shannon range: {diversity_results['shannon_diversity'].min():.3f} ~ {diversity_results['shannon_diversity'].max():.3f}")

    # 合并回 fishnet
    result = fishnet.merge(diversity_results, on='grid_id', how='left')

    # 填充没有数据的网格
    result['species_count'] = result['species_count'].fillna(0).astype(int)
    result['species_richness'] = result['species_richness'].fillna(0).astype(int)
    result['shannon_diversity'] = result['shannon_diversity'].fillna(0)

    # 重命名列
    result = result.rename(columns={
        'species_count': f'{taxa.lower()}_count',
        'species_richness': f'{taxa.lower()}_richness',
        'shannon_diversity': f'{taxa.lower()}_shannon'
    })

    return result


def main():
    print("=" * 50)
    print("Shannon Diversity Index Calculator")
    print("=" * 50)

    # 读取 fishnet
    fishnet = gpd.read_file("data/fishnet/fishnet.shp")
    print(f"Fishnet: {len(fishnet)} grids")

    # 计算鸟类的 diversity
    fishnet = calculate_diversity_for_taxa("Aves", fishnet)

    # 计算植物的 diversity
    fishnet = calculate_diversity_for_taxa("Plantae", fishnet)

    # 保存结果
    output_shp = OUTPUT_DIR / "fishnet_diversity.shp"
    fishnet.to_file(output_shp)
    print(f"\nSaved: {output_shp}")

    output_geojson = OUTPUT_DIR / "fishnet_diversity.geojson"
    fishnet.to_file(output_geojson, driver="GeoJSON")
    print(f"Saved: {output_geojson}")

    # 统计
    print("\n" + "=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Grids with birds:  {(fishnet['aves_count'] > 0).sum()}")
    print(f"Grids with plants: {(fishnet['plantae_count'] > 0).sum()}")
    print(f"Grids with both:   {((fishnet['aves_count'] > 0) & (fishnet['plantae_count'] > 0)).sum()}")
    print()
    print(f"Avg bird Shannon:  {fishnet[fishnet['aves_count'] > 0]['aves_shannon'].mean():.3f}")
    print(f"Avg plant Shannon: {fishnet[fishnet['plantae_count'] > 0]['plantae_shannon'].mean():.3f}")


if __name__ == "__main__":
    main()
