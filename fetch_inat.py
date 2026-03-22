"""
iNaturalist 数据爬虫 - Singapore Downtown Core
鸟类: 2015-2025
植物: 全部
"""

import requests
import time
import json
import pandas as pd
from pathlib import Path

# 配置
PLACE_ID = 120474  # Singapore Downtown
BASE_URL = "https://api.inaturalist.org/v1/observations"
OUTPUT_DIR = Path("data")
OUTPUT_DIR.mkdir(exist_ok=True)

REQUEST_DELAY = 1


def fetch_observations(taxa: str, year: int = None, per_page: int = 200) -> list:
    """爬取观察数据"""
    all_results = []
    page = 1
    total_pages = None

    year_str = f" {year}" if year else ""
    print(f"  Fetching {taxa}{year_str}...")

    while True:
        params = {
            "place_id": PLACE_ID,
            "iconic_taxa": taxa,
            "per_page": per_page,
            "page": page,
        }
        if year:
            params["year"] = year

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

            print(f"    Page {page}/{total_pages}, got {len(all_results)} records")

            if page >= total_pages:
                break

            page += 1
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"    Error: {e}")
            break

    return all_results


def extract_fields(observations: list) -> list:
    """提取关键字段"""
    extracted = []
    for obs in observations:
        item = {
            "id": obs.get("id"),
            "taxon_id": obs.get("taxon_id"),
            "taxon_name": obs.get("taxon", {}).get("name") if obs.get("taxon") else None,
            "common_name": obs.get("species_guess"),
            "iconic_taxon_name": obs.get("iconic_taxon_name"),
            "latitude": obs.get("latitude") or obs.get("geojson", {}).get("coordinates", [None, None])[1],
            "longitude": obs.get("longitude") or obs.get("geojson", {}).get("coordinates", [None, None])[0],
            "observed_on": obs.get("observed_on"),
            "time_observed_at": obs.get("time_observed_at"),
            "quality_grade": obs.get("quality_grade"),
            "user_login": obs.get("user", {}).get("login") if obs.get("user") else None,
            "place_guess": obs.get("place_guess"),
            "description": obs.get("description"),
            "num_identifications": obs.get("num_identifications"),
            "created_at": obs.get("created_at"),
            "updated_at": obs.get("updated_at"),
        }
        photos = obs.get("photos", [])
        item["photo_url"] = photos[0].get("url") if photos else None
        extracted.append(item)
    return extracted


def main():
    print("=" * 50)
    print("iNaturalist Crawler - Singapore Downtown Core")
    print("=" * 50)

    # ========== 鸟类: 2015-2025 ==========
    print("\n[Birds (Aves) 2015-2025]")
    all_birds = []

    for year in range(2015, 2026):
        observations = fetch_observations("Aves", year)
        all_birds.extend(observations)
        time.sleep(1)

    # 去重
    seen = set()
    unique_birds = []
    for obs in all_birds:
        obs_id = obs.get("id")
        if obs_id not in seen:
            seen.add(obs_id)
            unique_birds.append(obs)

    birds_data = extract_fields(unique_birds)
    df_birds = pd.DataFrame(birds_data)
    df_birds.to_csv(OUTPUT_DIR / "sg_downtown_aves.csv", index=False, encoding="utf-8-sig")
    print(f"\n  Saved: sg_downtown_aves.csv ({len(birds_data)} records)")

    # ========== 植物: 全部 ==========
    print("\n[Plants (Plantae) - All]")
    plants = fetch_observations("Plantae")
    plants_data = extract_fields(plants)
    df_plants = pd.DataFrame(plants_data)
    df_plants.to_csv(OUTPUT_DIR / "sg_downtown_plantae.csv", index=False, encoding="utf-8-sig")
    print(f"\n  Saved: sg_downtown_plantae.csv ({len(plants_data)} records)")

    # ========== 合并 ==========
    all_data = birds_data + plants_data
    df_all = pd.DataFrame(all_data)
    df_all.to_csv(OUTPUT_DIR / "sg_downtown_all.csv", index=False, encoding="utf-8-sig")
    print(f"\n  Saved: sg_downtown_all.csv ({len(all_data)} records)")

    print("\n" + "=" * 50)
    print("Done!")
    print(f"Birds (2015-2025): {len(birds_data)}")
    print(f"Plants (all):      {len(plants_data)}")
    print(f"Total:             {len(all_data)}")
    print("=" * 50)


if __name__ == "__main__":
    main()
