"""
iNaturalist 数据爬虫 - 基于 Fishnet 范围
时间范围: 2020-01 到 2026-01
"""

import requests
import time
import json
import pandas as pd
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

# 配置
BASE_URL = "https://api.inaturalist.org/v1/observations"
OUTPUT_DIR = Path("data")
REQUEST_DELAY = 1

# Fishnet bounding box (WGS84)
BBOX = {
    'swlat': 1.268708,
    'swlng': 103.841355,
    'nelat': 1.304902,
    'nelng': 103.869232
}

# 时间范围
DATE_RANGE = {
    'd1': '2020-01-01',
    'd2': '2026-01-31'
}


def fetch_observations(taxa: str, per_page: int = 200) -> list:
    """爬取指定类别的数据"""
    all_results = []
    page = 1
    total_pages = None

    print(f"  Fetching {taxa}...")

    while True:
        params = {
            "swlat": BBOX['swlat'],
            "swlng": BBOX['swlng'],
            "nelat": BBOX['nelat'],
            "nelng": BBOX['nelng'],
            "iconic_taxa": taxa,
            "d1": DATE_RANGE['d1'],
            "d2": DATE_RANGE['d2'],
            "per_page": per_page,
            "page": page,
        }

        try:
            response = requests.get(BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if not results:
                break

            all_results.extend(results)

            if total_pages is None:
                total_results = data.get("total_results", 0)
                total_pages = (total_results + per_page - 1) // per_page
                print(f"    Total: {total_results} records, {total_pages} pages")

            print(f"    Page {page}/{total_pages}, got {len(all_results)}")

            if page >= total_pages:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"    Error: {e}")
            break

    return all_results


def to_geodataframe(observations: list, crs: str = "EPSG:4326") -> gpd.GeoDataFrame:
    """转换为 GeoDataFrame"""
    records = []
    geometries = []

    for obs in observations:
        lat = obs.get("latitude") or obs.get("geojson", {}).get("coordinates", [None, None])[1]
        lng = obs.get("longitude") or obs.get("geojson", {}).get("coordinates", [None, None])[0]

        if lat is None or lng is None:
            continue

        records.append({
            "id": obs.get("id"),
            "taxon_id": obs.get("taxon_id"),
            "taxon_name": obs.get("taxon", {}).get("name") if obs.get("taxon") else None,
            "common_name": obs.get("species_guess"),
            "iconic_taxon_name": obs.get("iconic_taxon_name"),
            "observed_on": obs.get("observed_on"),
            "quality_grade": obs.get("quality_grade"),
            "user_login": obs.get("user", {}).get("login") if obs.get("user") else None,
        })
        geometries.append(Point(lng, lat))

    gdf = gpd.GeoDataFrame(records, geometry=geometries, crs=crs)
    return gdf


def main():
    print("=" * 50)
    print("iNaturalist Crawler - Fishnet Area")
    print(f"Date range: {DATE_RANGE['d1']} to {DATE_RANGE['d2']}")
    print("=" * 50)

    # 读取 fishnet
    fishnet = gpd.read_file("data/fishnet/fishnet.shp")
    print(f"\nFishnet: {len(fishnet)} grids, CRS: {fishnet.crs}")

    results = {}

    for taxa, name in [("Aves", "Birds"), ("Plantae", "Plants")]:
        print(f"\n[{name}]")
        observations = fetch_observations(taxa)

        # 转换为 GeoDataFrame
        gdf = to_geodataframe(observations)
        print(f"  Points with coords: {len(gdf)}")

        # 转换到 fishnet 的 CRS
        gdf = gdf.to_crs(fishnet.crs)

        # 用 fishnet 边界精确过滤（bounding box 可能会多捞一些点）
        fishnet_union = fishnet.geometry.unary_union
        gdf = gdf[gdf.geometry.within(fishnet_union)]
        print(f"  Points within fishnet: {len(gdf)}")

        # 保存 GeoJSON
        output_geojson = OUTPUT_DIR / f"inat_{taxa.lower()}.geojson"
        gdf.to_file(output_geojson, driver="GeoJSON")
        print(f"  Saved: {output_geojson}")

        results[taxa] = gdf
        time.sleep(2)

    print("\n" + "=" * 50)
    print("Done!")
    print(f"Birds:  {len(results['Aves'])} points")
    print(f"Plants: {len(results['Plantae'])} points")
    print("=" * 50)


if __name__ == "__main__":
    main()
