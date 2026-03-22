# Urban Agroecology Analysis for Singapore Downtown Core

This project analyzes potential urban farm sites in Singapore's Downtown Core, connecting them to nearby food/retail POIs and recommending crops to grow based on restaurant menu analysis and local biodiversity data.

## Overview

The project uses a multi-phase approach to identify urban farming opportunities:

1. **Spatial Analysis**: Identify farm sites by typology (podium, rooftops, streetscapes, green_spaces)
2. **Network Analysis**: Connect farms to nearby POIs within walking distance (400m/800m)
3. **Biodiversity Analysis**: Incorporate iNaturalist species observations
4. **Restaurant Analysis**: Use VLM (Vision Language Model) to analyze restaurant photos and identify farmable ingredients
5. **Crop Recommendations**: Generate crop recommendations based on restaurant demand and local growing conditions

## Project Structure

```
urban-vitality-bio/
├── data/                    # Raw data (iNaturalist, fishnet shapefiles)
├── farm/                    # Farm geometry inputs
├── json/                    # POI data (food, social, cultural)
├── cache/                   # API response cache and downloaded photos
├── farm_reports/            # Generated per-farm JSON analysis reports
├── farm_with_clusters/      # Farm data with cluster/phase assignments
├── network_visualization/   # Network connection maps and statistics
├── demo/                    # Demo visualization outputs
│
├── farm_micro_analysis.py   # Core farm analysis module
├── visualize_network.py     # Network visualization script
├── automate_phase1.py       # Restaurant photo download automation
├── batch_mcp_analyzer.py    # VLM batch analysis script
├── prepare_demo_data.py     # Demo data aggregation
├── visualize_farm_demo.py   # Interactive map generation
└── restaurant_vlm_analyzer.py # VLM photo analysis module
```

## Key Commands

```bash
# Run main farm micro-analysis (without APIs)
python farm_micro_analysis.py

# Run with specific phase filter
python farm_micro_analysis.py --phase 1

# Run with all APIs enabled (requires API keys)
python farm_micro_analysis.py --use-google-api --use-vlm-api

# Generate network visualization
python visualize_network.py

# Download restaurant photos for Phase 1
python automate_phase1.py

# Batch analyze photos via VLM
python batch_mcp_analyzer.py --batch-size 5 --limit 10

# Generate demo visualization
python prepare_demo_data.py
python visualize_farm_demo.py
```

## Architecture

### Data Pipeline

1. **iNaturalist Data** (`fetch_inat.py`) → Species observations for biodiversity analysis
2. **Fishnet Grid** (`fetch_fishnet_area.py`) → Spatial tessellation for clustering
3. **Diversity Calculation** (`calculate_diversity.py`) → Shannon diversity index per grid cell
4. **Cluster Analysis** (`cluster_analysis.py`) → Categorize areas by activity type
5. **Farm Assignment** (`assign_clusters_to_farms.py`, `assign_phases_to_farms.py`) → Link farms to clusters and development phases

### Analysis Modules

- **`FarmMicroAnalyzer`** (farm_micro_analysis.py) - Core class that analyzes individual farm sites
- **`RestaurantPhotoAnalyzer`** (restaurant_vlm_analyzer.py) - Fetches and analyzes restaurant photos with VLM
- **`GooglePlacesClient`** (google_places_client.py) - Wrapper for Google Places API with caching

## Coordinate Systems

- **Projected**: EPSG:32648 (UTM Zone 48N) - for distance calculations
- **Geographic**: EPSG:4326 (WGS84) - for API calls and GeoJSON output

## Key Thresholds

- Walking distance: 400m (5-minute walk), 800m (10-minute walk)
- Species buffer: 1200m around each farm
- POI matching: 10m threshold for connection attribution

## Cluster Types

| Cluster | Connects To | Focus |
|---------|-------------|-------|
| Cultural-Economic | Food, Social | Social activities |
| Economic-Only | Food, Social, Cultural | All activities |
| Socio-Economic | Food, Cultural | Cultural activities |
| Low-Activity | None | Biodiversity only |

## Phase Priority

1. Phase 1 - Aggressive (highest priority)
2. Phase 2 - High Priority
3. Phase 3 - Medium Priority
4. Phase 4 - Later Phase

## Environment Variables

```bash
GOOGLE_PLACES_API_KEY=your_key_here     # For restaurant data and photos
ANTHROPIC_API_KEY=your_key_here         # For VLM photo analysis
LLM_MODEL=glm-4.6v                      # VLM model for image analysis
```

## Dependencies

Primary: geopandas, pandas, numpy, shapely, requests, matplotlib

API integrations: Google Places API, Anthropic/VLM API (via MCP tools)

## Demo Visualization

The demo visualization (`demo/farm_demo.html`) shows:
- Phase 1 farm locations with typologies
- Servable restaurants (those where ingredients can be locally grown)
- Connection lines between farms and restaurants
- Crop recommendations per farm

Open in browser after running:
```bash
python prepare_demo_data.py
python visualize_farm_demo.py
```

## Recent Fixes

### Farm ID Mismatch (March 2026)

Fixed a critical bug where network connections used DataFrame index instead of actual FID column, causing:
- Restaurants to be associated with wrong farms
- VLM analysis to process restaurants for wrong farms

The fix ensures `farm_id` in network connections correctly maps to the FID column in farm geometries.

## License

MIT License
