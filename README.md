# Urban Agroecology Analysis for Singapore Downtown Core

This project analyzes potential urban farm sites in Singapore's Downtown Core, connecting them to nearby food/retail POIs and recommending crops to grow based on restaurant menu analysis and local biodiversity data.

## Methodology Overview

### 1. Spatial Data Pipeline

| Stage | Script | Method |
|-------|--------|--------|
| Data Acquisition | `fetch_inat.py`, `fetch_fishnet_area.py` | iNaturalist species data + fishnet grid tessellation |
| Diversity Analysis | `calculate_diversity.py` | Shannon Diversity Index: H' = -Σ(pᵢ × ln(pᵢ)) |
| Spatial Clustering | `cluster_analysis.py` | K-Means (k=4) on normalized activity dimensions |
| Farm Assignment | `assign_clusters_to_farms.py`, `assign_phases_to_farms.py` | Area-weighted spatial overlay |

### 2. Core Analysis

**Farm Micro-Analysis** (`farm_micro_analysis.py`):
- Walking distance thresholds: 400m (primary), 800m (secondary)
- Species buffer: 1200m radius for biodiversity inventory
- POI matching: 10m accuracy threshold

**Species Recommendation** (`species_classifier.py`):
- LLM-powered classification (indigenous/invasive/edible)
- Priority: Indigenous+Edible > Indigenous OR Edible > Non-invasive

**Restaurant Intelligence** (`restaurant_vlm_analyzer.py`):
- Google Places API → fetch restaurant photos
- VLM analysis → identify farmable ingredients
- Crop categorization: leafy greens, herbs, aromatics, vegetables

### 3. Cluster-Based Connection Strategy

| Cluster | Connects To | Focus |
|---------|-------------|-------|
| Cultural-Economic | Food, Social | Social activities |
| Economic-Only | Food, Social, Cultural | All activities |
| Socio-Economic | Food, Cultural | Cultural activities |
| Low-Activity | None | Biodiversity only |

### 4. Development Phasing

1. **Phase 1** - Aggressive (highest vitality areas)
2. **Phase 2** - High Priority
3. **Phase 3** - Medium Priority
4. **Phase 4** - Later Phase

## Project Structure

```
urban-vitality-bio/
├── data/                    # Raw data (iNaturalist, fishnet shapefiles)
├── farm/                    # Farm geometry inputs
├── json/                    # POI data (food, social, cultural)
├── cache/                   # API response cache and downloaded photos
├── farm_with_clusters/      # Farm data with cluster/phase assignments
├── network_visualization/   # Network connection GeoJSON files
│
│  # Core Pipeline Scripts
├── fetch_inat.py            # iNaturalist data acquisition
├── fetch_fishnet_area.py    # Fishnet grid generation
├── calculate_diversity.py   # Shannon diversity calculation
├── cluster_analysis.py      # K-Means clustering
├── assign_clusters_to_farms.py
├── assign_phases_to_farms.py
│
│  # Core Analysis Modules
├── farm_micro_analysis.py   # Main farm analysis engine
├── restaurant_vlm_analyzer.py # VLM photo analysis
├── google_places_client.py  # Google Places API wrapper
├── species_classifier.py    # Species classification
│
│  # Visualization
├── visualize_network.py     # Network visualization
├── visualize_micro_analysis.py
├── automate_phase1.py       # Photo download automation
│
│  # Batch Processing (see note below)
├── batch_mcp_analyzer.py    # VLM batch analysis entry point
└── mcp_batch_processor.py   # Batch processing logic
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
```

## Batch Processing Note

Due to MCP (Model Context Protocol) call rate limits, VLM photo analysis is performed in batches using temporary scripts (`save_batch*.py`, `process_remaining.py`, etc.). These scripts are **not part of the core methodology** but serve as practical workarounds for API constraints. The entry point for batch processing is:

```bash
python batch_mcp_analyzer.py --batch-size 5 --limit 10
```

Batch scripts are excluded from version control via `.gitignore` but can be regenerated if needed.

## Coordinate Systems

- **Projected**: EPSG:32648 (UTM Zone 48N) - for distance calculations
- **Geographic**: EPSG:4326 (WGS84) - for API calls and GeoJSON output

## Environment Variables

```bash
GOOGLE_PLACES_API_KEY=your_key_here     # For restaurant data and photos
ANTHROPIC_API_KEY=your_key_here         # For VLM photo analysis
LLM_MODEL=glm-4.6v                      # VLM model for image analysis
```

## Dependencies

Primary: geopandas, pandas, numpy, shapely, requests, matplotlib

API integrations: Google Places API, Anthropic/VLM API (via MCP tools)

## Findings

*To be added with visualizations from `network_visualization/`.*

## License

MIT License

> **TODO**: Document data sources and their licenses:
> - iNaturalist observations (CC0/CC-BY/CC-BY-NC)
> - Singapore government open data
> - Google Places API terms of use
> - Any other third-party datasets
