import pandas as pd
import folium
import json
import os
import numpy as np
from flask import Flask, render_template

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')

app = Flask(__name__, template_folder=template_dir)

@app.route('/')
def index():
    return render_template('index.html')

def run_data_pipeline():
    # File Paths
    TREE_DATA = os.path.join(base_dir, 'data', '2015_Street_Tree_Census_-_Tree_Data_20260315.csv')
    INCOME_DATA = os.path.join(base_dir, 'data', 'ACSST5Y2024.S1901-Data.csv')
    NTA_MAPPING = os.path.join(base_dir, 'data', '2020_Census_Tracts_to_2020_NTAs_and_CDTAs_Equivalency_20260414.csv')
    
    # 1. Income
    inc = pd.read_csv(INCOME_DATA, skiprows=[1])
    inc['median_income'] = pd.to_numeric(inc['S1901_C01_012E'].astype(str).str.replace(',', '').str.replace('+', ''), errors='coerce')
    inc['zip_code'] = inc['GEO_ID'].str.split('US').str[-1]
    
    # 2. Trees
    trees = pd.read_csv(TREE_DATA)
    trees = trees[trees['status'] == 'Alive'].copy()
    trees['health_numeric'] = trees['health'].map({'Good': 3, 'Fair': 2, 'Poor': 1})
    trees['postcode'] = trees['postcode'].astype(str).str.strip()

    # 3. NTA Sync
    nta_df = pd.read_csv(NTA_MAPPING)
    def normalize_tract(val):
        try: return str(int(float(str(val).replace(',', ''))))
        except: return None
    trees['CT_Normalized'] = trees['census tract'].apply(normalize_tract)
    nta_df['CT_Normalized'] = nta_df['CT2020'].apply(normalize_tract)

    # 4. Merge
    tree_with_neighborhoods = trees.merge(nta_df[['CT_Normalized', 'NTACode', 'BoroName']], on='CT_Normalized', how='inner')
    trees_with_income = tree_with_neighborhoods.merge(inc[['zip_code', 'median_income']], left_on='postcode', right_on='zip_code', how='inner')

    # 5. Stats
    neighborhood_stats = trees_with_income.groupby(['NTACode', 'BoroName'], as_index=False).agg(
        avg_health=('health_numeric', 'mean'),
        avg_income=('median_income', 'mean')
    )
    
    # Borough Correlations
    borough_corrs = neighborhood_stats.groupby('BoroName').apply(
        lambda x: x['avg_income'].corr(x['avg_health']) if len(x) > 1 else 0,
        include_groups=False
    ).reset_index()
    borough_corrs.columns = ['BoroName', 'Boro_Correlation']

    final_df = neighborhood_stats.merge(borough_corrs, on='BoroName')
    final_df['NTACode'] = final_df['NTACode'].astype(str).str.strip()
    return final_df

def create_map(df):
    geojson_path = os.path.join(base_dir, 'data', '2020_Neighborhood_Tabulation_Areas_(NTAs)_20260414.geojson')
    
    with open(geojson_path, 'r') as f:
        nyc_geojson = json.load(f)

    # --- THE SYNTAX FIX: Remove colons from GeoJSON property keys ---
    for feature in nyc_geojson['features']:
        # Create a new dictionary without colons in keys
        clean_props = {}
        for k, v in feature['properties'].items():
            clean_key = k.replace(':', '') # ':id' becomes 'id'
            clean_props[clean_key] = v
        feature['properties'] = clean_props

    # Initialize map
    m = folium.Map(location=[40.7128, -73.9352], zoom_start=11, tiles="CartoDB positron")

    # Add the Choropleth using 'nta2020' (the clean version of ':nta2020' if it had one)
    folium.Choropleth(
        geo_data=nyc_geojson,
        data=df,
        columns=["NTACode", "Boro_Correlation"],
        key_on="feature.properties.nta2020", # This name is now clean of colons
        fill_color="YlGnBu",
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name="Wealth vs. Tree Health Correlation",
        highlight=True
    ).add_to(m)

    # Original Borough Labels
    boroughs = {
        "Manhattan": [40.7831, -73.9712],
        "Brooklyn": [40.6782, -73.9442],
        "Queens": [40.7282, -73.7949],
        "The Bronx": [40.8448, -73.8648],
        "Staten Island": [40.5795, -74.1502],
    }
    for name, coords in boroughs.items():
        folium.Marker(
            location=coords,
            icon=folium.DivIcon(html=f'<div style="font-size:14px; font-weight:bold; color:black">{name}</div>')
        ).add_to(m)

    if not os.path.exists(template_dir): os.makedirs(template_dir)
    m.save(os.path.join(template_dir, 'index.html'))

if __name__ == '__main__':
    processed_data = run_data_pipeline()
    if not processed_data.empty:
        create_map(processed_data)
        app.run(debug=True, use_reloader=False)