"""
Interactive Farm-to-Restaurant Demo Visualization

Creates a single HTML file with an interactive map showing:
- Phase 1 farm locations with typologies
- Servable restaurants with local sourcing potential
- Connection lines between farms and restaurants
- Summary statistics panel
"""

import json
import folium
from folium import plugins
from pathlib import Path
import geopandas as gpd
import pandas as pd

# Configuration
DEMO_DATA_PATH = Path('demo/demo_data.json')
FARM_GEOJSON = 'farm_with_clusters/all_farm_phases.geojson'
OUTPUT_PATH = Path('demo/farm_demo.html')

CRS_GEOGRAPHIC = 'EPSG:4326'

# Colors
TYPOLOGY_COLORS = {
    'podium': '#e41a1c',      # Red
    'rooftops': '#377eb8',    # Blue
    'streetscapes': '#4daf4a', # Green
    'green_spaces': '#984ea3'  # Purple
}

CLUSTER_COLORS = {
    'Cultural-Economic': '#2ca02c',
    'Economic-Only': '#9467bd',
    'Low-Activity': '#8c564b',
    'Socio-Economic': '#1f77b4'
}


def load_demo_data():
    """Load processed demo data."""
    with open(DEMO_DATA_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_farm_geometries():
    """Load farm geometries for Phase 1 farms."""
    farms = gpd.read_file(FARM_GEOJSON)
    farms = farms.to_crs(CRS_GEOGRAPHIC)
    phase1 = farms[farms['phase'] == 1].copy()
    return phase1


def create_farm_popup(farm_data):
    """Create HTML popup content for a farm."""
    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 280px; max-width: 400px;">
        <h3 style="margin: 0 0 10px 0; color: #2c3e50;">Farm #{farm_data['farm_id']}</h3>
        <table style="width: 100%; font-size: 12px;">
            <tr><td><b>Typology:</b></td><td>{farm_data['typology']}</td></tr>
            <tr><td><b>Cluster:</b></td><td>{farm_data['cluster']}</td></tr>
            <tr><td><b>Area:</b></td><td>{farm_data['area_sqm']:.1f} sqm</td></tr>
            <tr><td><b>Restaurants Analyzed:</b></td><td>{farm_data['total_restaurants_analyzed']}</td></tr>
            <tr><td><b>Servable:</b></td><td style="color: green;"><b>{farm_data['total_servable']}</b></td></tr>
        </table>
    """

    # Add recommended crops
    crops = farm_data.get('recommended_crops', {})
    if any(crops.values()):
        html += "<h4 style='margin: 10px 0 5px 0; color: #27ae60;'>Recommended Crops</h4>"

        for category, items in crops.items():
            if items:
                category_name = category.replace('_', ' ').title()
                html += f"<div style='font-size: 11px; margin-bottom: 5px;'>"
                html += f"<b>{category_name}:</b> {', '.join(items[:8])}"
                if len(items) > 8:
                    html += f" <i>(+{len(items)-8} more)</i>"
                html += "</div>"

    # Add servable restaurants list
    servable = farm_data.get('servable_restaurants', [])
    if servable:
        html += f"<h4 style='margin: 10px 0 5px 0; color: #2980b9;'>Servable Restaurants ({len(servable)})</h4>"
        html += "<div style='max-height: 150px; overflow-y: auto; font-size: 11px;'>"
        for rest in servable[:10]:
            cuisines = ', '.join(rest.get('cuisine_types', [])) or 'Unknown'
            can_provide = rest.get('can_provide', [])
            html += f"""
            <div style='padding: 3px 0; border-bottom: 1px solid #eee;'>
                <b>{rest['name']}</b><br>
                <span style='color: #666;'>{cuisines}</span><br>
                <span style='color: #27ae60; font-size: 10px;'>Can provide: {', '.join(can_provide[:5])}{'...' if len(can_provide) > 5 else ''}</span>
            </div>
            """
        if len(servable) > 10:
            html += f"<i style='color: #666;'>... and {len(servable) - 10} more</i>"
        html += "</div>"

    html += "</div>"
    return html


def create_restaurant_popup(rest_data, farm_id):
    """Create HTML popup content for a restaurant."""
    is_servable = rest_data.get('is_servable', False)
    status_color = '#27ae60' if is_servable else '#e74c3c'
    status_text = 'Servable' if is_servable else 'Not Servable'

    html = f"""
    <div style="font-family: Arial, sans-serif; min-width: 250px; max-width: 350px;">
        <h3 style="margin: 0 0 10px 0; color: #2c3e50;">{rest_data['name']}</h3>
        <span style="background: {status_color}; color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{status_text}</span>
        <table style="width: 100%; font-size: 12px; margin-top: 10px;">
            <tr><td><b>Cuisine:</b></td><td>{', '.join(rest_data.get('cuisine_types', ['Unknown']))}</td></tr>
            <tr><td><b>Near Farm:</b></td><td>#{farm_id}</td></tr>
        </table>
    """

    if is_servable:
        can_provide = rest_data.get('can_provide', [])
        cannot_provide = rest_data.get('cannot_provide', [])

        html += f"""
        <div style="margin-top: 10px;">
            <h4 style="margin: 0 0 5px 0; color: #27ae60;">Can Provide ({len(can_provide)})</h4>
            <div style="font-size: 11px; color: #27ae60;">{', '.join(can_provide[:10])}{'...' if len(can_provide) > 10 else ''}</div>
        </div>
        """

        if cannot_provide:
            html += f"""
            <div style="margin-top: 10px;">
                <h4 style="margin: 0 0 5px 0; color: #e74c3c;">Cannot Provide ({len(cannot_provide)})</h4>
                <div style="font-size: 11px; color: #e74c3c;">{', '.join(cannot_provide[:5])}</div>
            </div>
            """

        # Growing recommendations
        growing = rest_data.get('growing_recommendations', {})
        if growing:
            html += "<div style='margin-top: 10px; font-size: 11px;'>"
            html += "<b>Growing Tips:</b><br>"
            if growing.get('quick_wins'):
                html += f"<span style='color: #f39c12;'>Quick wins:</span> {', '.join(growing['quick_wins'][:5])}<br>"
            html += "</div>"

    html += "</div>"
    return html


def create_summary_panel(summary):
    """Create HTML for the summary statistics panel."""
    html = f"""
    <div style="position: fixed; top: 10px; left: 50px; z-index: 9999;
                background: white; padding: 15px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial, sans-serif;
                min-width: 250px;">
        <h3 style="margin: 0 0 10px 0; color: #2c3e50;">Farm-to-Restaurant Demo</h3>
        <hr style="margin: 10px 0;">
        <table style="width: 100%; font-size: 12px;">
            <tr><td>Phase 1 Farms:</td><td style="text-align: right;"><b>{summary['total_phase1_farms']}</b></td></tr>
            <tr><td>Farms with Analysis:</td><td style="text-align: right;"><b>{summary['farms_with_restaurants']}</b></td></tr>
            <tr><td>Restaurants Analyzed:</td><td style="text-align: right;"><b>{summary['total_restaurants_analyzed']}</b></td></tr>
            <tr><td>Servable Restaurants:</td><td style="text-align: right; color: #27ae60;"><b>{summary['total_servable_restaurants']}</b></td></tr>
            <tr><td>Servable %:</td><td style="text-align: right;"><b>{summary['servable_percentage']}%</b></td></tr>
        </table>
        <hr style="margin: 10px 0;">
        <h4 style="margin: 0 0 5px 0; color: #2c3e50;">Top Crops</h4>
        <div style="font-size: 11px; max-height: 120px; overflow-y: auto;">
    """

    for crop, count in summary['most_common_crops'][:10]:
        html += f"<div style='display: flex; justify-content: space-between; padding: 2px 0;'>"
        html += f"<span>{crop}</span><span style='color: #666;'>{count}</span></div>"

    html += """
        </div>
    </div>
    """
    return html


def create_map(demo_data, farm_gdf):
    """Create the interactive Folium map."""
    # Calculate map center
    all_lats = [f['centroid'][0] for f in demo_data['farms']]
    all_lons = [f['centroid'][1] for f in demo_data['farms']]
    center_lat = sum(all_lats) / len(all_lats)
    center_lon = sum(all_lons) / len(all_lons)

    # Create base map
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=15,
        tiles='cartodbpositron'
    )

    # Create feature groups for layers
    farms_group = folium.FeatureGroup(name='Phase 1 Farms', show=True)
    restaurants_group = folium.FeatureGroup(name='Servable Restaurants', show=True)
    connections_group = folium.FeatureGroup(name='Connections', show=True)

    # Add farms to map
    farm_id_to_data = {f['farm_id']: f for f in demo_data['farms']}

    for idx, row in farm_gdf.iterrows():
        # Get farm_id
        farm_id = row.get('FID')
        if farm_id is None or (isinstance(farm_id, float) and str(farm_id) == 'nan'):
            farm_id = row.get('Id')
        if farm_id is None or (isinstance(farm_id, float) and str(farm_id) == 'nan'):
            farm_id = idx
        farm_id = int(farm_id)

        farm_data = farm_id_to_data.get(farm_id)
        if not farm_data:
            continue

        typology = farm_data.get('typology', 'unknown')
        color = TYPOLOGY_COLORS.get(typology, '#999999')

        # Get farm geometry coordinates
        geom = row.geometry
        if geom.geom_type == 'Polygon':
            coords = [[lat, lon] for lon, lat in geom.exterior.coords]
        elif geom.geom_type == 'MultiPolygon':
            coords = [[lat, lon] for lon, lat in geom.geoms[0].exterior.coords]
        else:
            continue

        # Create farm polygon
        popup_html = create_farm_popup(farm_data)
        popup = folium.Popup(popup_html, max_width=450)

        folium.Polygon(
            locations=coords,
            color=color,
            weight=2,
            fill=True,
            fillColor=color,
            fillOpacity=0.4,
            popup=popup,
            tooltip=f"Farm #{farm_id} ({typology})"
        ).add_to(farms_group)

        # Add restaurant markers and connections for this farm
        for rest in farm_data.get('servable_restaurants', []):
            rest_lat = rest.get('lat')
            rest_lon = rest.get('lon')

            if rest_lat is None or rest_lon is None:
                continue

            # Restaurant marker
            rest_popup = folium.Popup(
                create_restaurant_popup(rest, farm_id),
                max_width=400
            )

            folium.CircleMarker(
                location=[rest_lat, rest_lon],
                radius=6,
                color='#27ae60',
                fill=True,
                fillColor='#27ae60',
                fillOpacity=0.7,
                popup=rest_popup,
                tooltip=rest['name']
            ).add_to(restaurants_group)

            # Connection line
            farm_centroid = farm_data['centroid']
            folium.PolyLine(
                locations=[farm_centroid, [rest_lat, rest_lon]],
                color='#3498db',
                weight=1,
                opacity=0.5,
                dash_array='5, 5'
            ).add_to(connections_group)

    # Add groups to map
    farms_group.add_to(m)
    restaurants_group.add_to(m)
    connections_group.add_to(m)

    # Add layer control
    folium.LayerControl().add_to(m)

    # Add summary panel as HTML
    summary_html = create_summary_panel(demo_data['summary'])
    m.get_root().html.add_child(folium.Element(summary_html))

    # Add legend
    legend_html = """
    <div style="position: fixed; bottom: 50px; left: 50px; z-index: 9999;
                background: white; padding: 15px; border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.2); font-family: Arial, sans-serif;">
        <h4 style="margin: 0 0 10px 0;">Legend</h4>
        <div style="font-size: 12px;">
            <div style="margin: 5px 0;">
                <span style="background: #e41a1c; width: 15px; height: 15px; display: inline-block; margin-right: 5px;"></span>
                Podium
            </div>
            <div style="margin: 5px 0;">
                <span style="background: #377eb8; width: 15px; height: 15px; display: inline-block; margin-right: 5px;"></span>
                Rooftop
            </div>
            <div style="margin: 5px 0;">
                <span style="background: #4daf4a; width: 15px; height: 15px; display: inline-block; margin-right: 5px;"></span>
                Streetscape
            </div>
            <div style="margin: 5px 0;">
                <span style="background: #984ea3; width: 15px; height: 15px; display: inline-block; margin-right: 5px;"></span>
                Green Space
            </div>
            <hr style="margin: 10px 0;">
            <div style="margin: 5px 0;">
                <span style="background: #27ae60; border-radius: 50%; width: 12px; height: 12px; display: inline-block; margin-right: 5px;"></span>
                Servable Restaurant
            </div>
        </div>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    return m


def main():
    print("=" * 60)
    print("Creating Interactive Farm Demo Visualization")
    print("=" * 60)

    # Load data
    print("\nLoading demo data...")
    demo_data = load_demo_data()

    print("Loading farm geometries...")
    farm_gdf = load_farm_geometries()

    # Create map
    print("\nCreating interactive map...")
    m = create_map(demo_data, farm_gdf)

    # Save map
    m.save(str(OUTPUT_PATH))
    print(f"\nMap saved to: {OUTPUT_PATH}")
    print(f"Open in browser: file://{OUTPUT_PATH.absolute()}")


if __name__ == '__main__':
    main()
