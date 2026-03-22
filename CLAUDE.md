# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Urban Agroecology Analysis for Singapore Downtown Core. This project analyzes potential urban farm sites, connects them to nearby food/retail POIs, and recommends crops to grow based on restaurant menu analysis and local biodiversity data.

## Key Commands

```bash
# Run main farm micro-analysis (without APIs)
python farm_micro_analysis.py

# Run with specific phase filter
python farm_micro_analysis.py --phase 1

# Run with all APIs enabled (requires API keys)
python farm_micro_analysis.py --use-google-api --use-vlm-api

# Run network visualization (generates connection maps)
python visualize_network.py

# Run Phase 1 photo automation (downloads restaurant photos)
python automate_phase1.py

# Batch analyze downloaded photos via MCP
python batch_mcp_analyzer.py --batch-size 5 --limit 10
```

## Architecture

### Data Pipeline
1. **iNaturalist Data** (`fetch_inat.py`) → Species observations for biodiversity analysis
2. **Fishnet Grid** (`fetch_fishnet_area.py`) → Spatial tessellation for clustering
3. **Diversity Calculation** (`calculate_diversity.py`) → Shannon diversity index per grid cell
4. **Cluster Analysis** (`cluster_analysis.py`) → Categorize areas by activity type
5. **Farm Assignment** (`assign_clusters_to_farms.py`, `assign_phases_to_farms.py`) → Link farms to clusters and development phases

### Analysis Modules
- **`FarmMicroAnalyzer`** (farm_micro_analysis.py) - Core class that analyzes individual farm sites, connected POIs, nearby species, and generates crop recommendations
- **`RestaurantPhotoAnalyzer`** (restaurant_vlm_analyzer.py) - Fetches restaurant photos from Google Places API and analyzes them with VLM to identify farmable ingredients
- **`GooglePlacesClient`** (google_places_client.py) - Wrapper for Google Places API with caching

### Coordinate Systems
- **Projected**: EPSG:32648 (UTM Zone 48N) - for distance calculations
- **Geographic**: EPSG:4326 (WGS84) - for API calls and GeoJSON output

### Key Thresholds
- Walking distance: 400m (5-minute walk), 800m (10-minute walk)
- Species buffer: 1200m around each farm
- POI matching: 10m threshold for connection attribution

### Cluster Types (determine POI connection strategy)
| Cluster | Connects To | Focus |
|---------|-------------|-------|
| Cultural-Economic | Food, Social | Social activities |
| Economic-Only | Food, Social, Cultural | All activities |
| Socio-Economic | Food, Cultural | Cultural activities |
| Low-Activity | None | Biodiversity only |

### Phase Priority
1. Phase 1 - Aggressive (highest priority)
2. Phase 2 - High Priority
3. Phase 3 - Medium Priority
4. Phase 4 - Later Phase

## Directory Structure

- `data/` - Raw data: iNaturalist exports, fishnet shapefiles, diversity/cluster results
- `farm/` - Farm geometry inputs (green_spaces.geojson, podium.geojson, rooftops.geojson, streetscapes.geojson)
- `json/` - POI data (food.geojson, social_dim.geojson, cultural_dim.geojson, inat_*.geojson)
- `cache/` - API response cache and downloaded restaurant photos
- `farm_reports/` - Generated per-farm JSON analysis reports
- `farm_with_clusters/` - Farm data with cluster/phase assignments
- `network_visualization/` - Network connection maps and statistics

## Environment Variables

```bash
GOOGLE_PLACES_API_KEY=your_key_here     # For restaurant data and photos
ANTHROPIC_API_KEY=your_key_here         # For VLM photo analysis
LLM_MODEL=glm-4.6v                      # VLM model for image analysis
```

## Dependencies

Primary: geopandas, pandas, numpy, shapely, requests, matplotlib

API integrations: Google Places API, Anthropic/VLM API (via MCP tools)
