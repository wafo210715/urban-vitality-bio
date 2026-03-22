"""
计算所有维度的 Shannon Diversity Index
- cultural_dim, economic_dim, social_dim: 基于 subcategor
- ecological_dim: 基于 aves + plantae 的 taxon_name，归一化后合并
"""

import geopandas as gpd
import pandas as pd
import numpy as np
from pathlib import Path

OUTPUT_DIR = Path("data")
JSON_DIR = Path("json")


def shannon_diversity(series: pd.Series) -> float:
    """计算 Shannon Diversity Index: H' = -Σ(pi * ln(pi))"""
    counts = series.value_counts()
    if len(counts) <= 1:
        return 0.0
    total = counts.sum()
    proportions = counts / total
    proportions = proportions[proportions > 0]
    return -np.sum(proportions * np.log(proportions))


def normalize(series: pd.Series) -> pd.Series:
    """Min-Max 归一化到 [0, 1]"""
    min_val = series.min()
    max_val = series.max()
    if max_val == min_val:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - min_val) / (max_val - min_val)


def calculate_dim_diversity(fishnet: gpd.GeoDataFrame, dim_name: str, group_col: str = 'subcategor') -> gpd.GeoDataFrame:
    """计算某个维度的 diversity"""

    gdf = gpd.read_file(JSON_DIR / f"{dim_name}.geojson")
    print(f"\n[{dim_name}] {len(gdf)} points")

    # 转换到 fishnet 的 CRS
    gdf = gdf.to_crs(fishnet.crs)

    # Spatial join
    joined = gpd.sjoin(gdf, fishnet[['grid_id', 'geometry']], how='left', predicate='within')
    print(f"  Points within fishnet: {joined['grid_id'].notna().sum()}")

    # 计算每个网格的 diversity
    results = joined.groupby('grid_id').agg(
        count=(group_col, 'count'),
        richness=(group_col, 'nunique'),
        shannon=(group_col, shannon_diversity)
    ).reset_index()

    print(f"  Grids with data: {len(results)}")

    # 合并回 fishnet
    col_prefix = dim_name.replace('_dim', '')
    result = fishnet.merge(results, on='grid_id', how='left')
    result = result.rename(columns={
        'count': f'{col_prefix}_count',
        'richness': f'{col_prefix}_richness',
        'shannon': f'{col_prefix}_shannon'
    })

    # 填充空值
    result[f'{col_prefix}_count'] = result[f'{col_prefix}_count'].fillna(0).astype(int)
    result[f'{col_prefix}_richness'] = result[f'{col_prefix}_richness'].fillna(0).astype(int)
    result[f'{col_prefix}_shannon'] = result[f'{col_prefix}_shannon'].fillna(0)

    # 归一化
    result[f'{col_prefix}_shannon_norm'] = normalize(result[f'{col_prefix}_shannon'])

    return result[[f'{col_prefix}_count', f'{col_prefix}_richness', f'{col_prefix}_shannon', f'{col_prefix}_shannon_norm', 'grid_id']]


def calculate_ecological_dim(fishnet: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """计算 ecological_dim: aves 和 plantae 的归一化合并"""

    results = fishnet[['grid_id']].copy()

    for taxa in ['aves', 'plantae']:
        gdf = gpd.read_file(JSON_DIR / f"inat_{taxa}.geojson")
        print(f"\n[inat_{taxa}] {len(gdf)} points")

        # 确保坐标系一致
        gdf = gdf.to_crs(fishnet.crs)

        # Spatial join
        joined = gpd.sjoin(gdf, fishnet[['grid_id', 'geometry']], how='left', predicate='within')
        print(f"  Points within fishnet: {joined['grid_id'].notna().sum()}")

        # 计算每个网格的 diversity
        div_results = joined.groupby('grid_id').agg(
            count=('taxon_name', 'count'),
            richness=('taxon_name', 'nunique'),
            shannon=('taxon_name', shannon_diversity)
        ).reset_index()

        # 合并
        results = results.merge(div_results, on='grid_id', how='left')
        results = results.rename(columns={
            'count': f'{taxa}_count',
            'richness': f'{taxa}_richness',
            'shannon': f'{taxa}_shannon'
        })

        # 填充空值
        results[f'{taxa}_count'] = results[f'{taxa}_count'].fillna(0).astype(int)
        results[f'{taxa}_richness'] = results[f'{taxa}_richness'].fillna(0).astype(int)
        results[f'{taxa}_shannon'] = results[f'{taxa}_shannon'].fillna(0)

    # 归一化 aves_shannon 和 plantae_shannon
    results['aves_shannon_norm'] = normalize(results['aves_shannon'])
    results['plantae_shannon_norm'] = normalize(results['plantae_shannon'])

    # 合并并再次归一化得到 ecological_shannon
    results['eco_combined'] = results['aves_shannon_norm'] + results['plantae_shannon_norm']
    results['eco_shannon_norm'] = normalize(results['eco_combined'])

    # 重命名为最终列名
    results = results.rename(columns={
        'eco_shannon_norm': 'eco_shannon'
    })

    return results


def main():
    print("=" * 60)
    print("Shannon Diversity Index Calculator - All Dimensions")
    print("=" * 60)

    # 读取 fishnet
    fishnet = gpd.read_file("data/fishnet/fishnet.shp")
    print(f"Fishnet: {len(fishnet)} grids, CRS: {fishnet.crs}")

    # 结果 DataFrame
    final_result = fishnet.copy()

    # 计算 cultural, economic, social 维度
    for dim in ['cultural_dim', 'economic_dim', 'social_dim']:
        dim_result = calculate_dim_diversity(fishnet, dim, 'subcategor')
        final_result = final_result.merge(dim_result, on='grid_id', how='left')

    # 计算 ecological 维度
    eco_result = calculate_ecological_dim(fishnet)
    final_result = final_result.merge(eco_result, on='grid_id', how='left')

    # 保存结果
    output_shp = OUTPUT_DIR / "fishnet_diversity.shp"
    final_result.to_file(output_shp)
    print(f"\n\nSaved: {output_shp}")

    output_geojson = OUTPUT_DIR / "fishnet_diversity.geojson"
    final_result.to_file(output_geojson, driver="GeoJSON")
    print(f"Saved: {output_geojson}")

    # 统计
    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    print("\nRaw Shannon Diversity:")
    for prefix in ['cultural', 'economic', 'social']:
        grids_with_data = (final_result[f'{prefix}_count'] > 0).sum()
        avg_shannon = final_result[final_result[f'{prefix}_count'] > 0][f'{prefix}_shannon'].mean()
        print(f"{prefix:10s}: {grids_with_data:4d} grids, avg = {avg_shannon:.3f}")

    print(f"{'aves':10s}: {(final_result['aves_count'] > 0).sum():4d} grids, avg = {final_result[final_result['aves_count'] > 0]['aves_shannon'].mean():.3f}")
    print(f"{'plantae':10s}: {(final_result['plantae_count'] > 0).sum():4d} grids, avg = {final_result[final_result['plantae_count'] > 0]['plantae_shannon'].mean():.3f}")

    print("\nNormalized (0-1):")
    for prefix in ['cultural', 'economic', 'social']:
        grids_with_data = (final_result[f'{prefix}_count'] > 0).sum()
        avg_norm = final_result[final_result[f'{prefix}_count'] > 0][f'{prefix}_shannon_norm'].mean()
        print(f"{prefix:10s}: avg = {avg_norm:.3f}")

    print(f"{'eco':10s}: {(final_result['eco_combined'] > 0).sum():4d} grids, avg = {final_result[final_result['eco_combined'] > 0]['eco_shannon'].mean():.3f}")


if __name__ == "__main__":
    main()
