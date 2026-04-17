import pandas as pd
import folium
import json
import os
import branca
import numpy as np
from flask import Flask, render_template

base_dir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(base_dir, 'templates')
if not os.path.exists(template_dir): os.makedirs(template_dir)

app = Flask(__name__)

# --- 1. DATA PIPELINE ---
def run_data_pipeline():
    TREE_DATA = os.path.join(base_dir, 'data', '2015_Street_Tree_Census_-_Tree_Data_20260315.csv')
    INCOME_DATA = os.path.join(base_dir, 'data', 'ACSST5Y2024.S1901-Data.csv')
    NTA_MAPPING = os.path.join(base_dir, 'data', '2020_Census_Tracts_to_2020_NTAs_and_CDTAs_Equivalency_20260414.csv')
    
    inc = pd.read_csv(INCOME_DATA, skiprows=[1])
    inc['median_income'] = pd.to_numeric(inc['S1901_C01_012E'].astype(str).str.replace(',', '').str.replace('+', ''), errors='coerce')
    inc['zip'] = inc['GEO_ID'].str.split('US').str[-1].str.strip()
    
    trees = pd.read_csv(TREE_DATA)
    trees = trees[trees['status'] == 'Alive'].copy()
    trees['h_num'] = trees['health'].map({'Good': 3, 'Fair': 2, 'Poor': 1})
    trees['postcode'] = trees['postcode'].astype(str).str.strip()

    def standardize_tract(val):
        try:
            s = str(int(float(val)))
            if len(s) <= 4: return s.zfill(4) + "00"
            return s.zfill(6)
        except: return "000000"

    trees['CT_Standard'] = trees['census tract'].apply(standardize_tract)
    nta_map = pd.read_csv(NTA_MAPPING)
    nta_map['CT_Standard'] = nta_map['CT2020'].apply(standardize_tract)

    merged = trees.merge(nta_map[['CT_Standard', 'NTACode', 'NTAName', 'BoroName']], on='CT_Standard')
    merged = merged.merge(inc[['zip', 'median_income']], left_on='postcode', right_on='zip')

    zip_tree_counts = trees.groupby('postcode').size().reset_index(name='total_zip_trees')
    merged = merged.merge(zip_tree_counts, on='postcode')

    CITY_AVG_HEALTH = merged['h_num'].mean()

    def calc_local_corr(group):
        if len(group) < 10 or group['median_income'].nunique() <= 1: return 0.0
        c = group['median_income'].corr(group['h_num'])
        return c if not np.isnan(c) else 0.0

    nta_corrs = merged.groupby('NTACode').apply(calc_local_corr, include_groups=False).reset_index(name='NTA_Correlation')

    species_counts = merged.groupby(['NTACode', 'spc_common']).size().reset_index(name='count')
    total_counts = merged.groupby('NTACode').size().reset_index(name='total')
    species_data = species_counts.merge(total_counts, on='NTACode')
    species_data['pct'] = (species_data['count'] / species_data['total'] * 100).round(1)
    
    def get_top_species(group):
        top = group[group['pct'] >= 1.0].sort_values(by='pct', ascending=False).head(10)
        return "".join([f"<p style='margin:2px 0;'>• <b>{str(row['spc_common']).title()}</b> ({row['pct']}%)</p>" for _, row in top.iterrows()])
    
    species_info = species_data.groupby('NTACode').apply(get_top_species, include_groups=False).reset_index(name='tree_list')

    health_stats = merged.groupby(['NTACode', 'spc_common']).agg(avg_health=('h_num', 'mean'), sample_size=('h_num', 'count')).reset_index()
    health_with_pct = health_stats.merge(species_data[['NTACode', 'spc_common', 'pct']], on=['NTACode', 'spc_common'])
    resilient_species = health_with_pct[health_with_pct['sample_size'] >= 5].merge(nta_corrs, on='NTACode')

    def get_resilience_advice(group, city_avg):
        avg_h = group['avg_health'].mean()
        status = "Non-vulnerable" if avg_h >= city_avg else "Vulnerable"
        corr_val = round(group['NTA_Correlation'].iloc[0], 3)
        best_trees = group.sort_values(by='avg_health', ascending=False).head(3)
        advice_list = "".join([f"<p style='margin:2px 0;'>• <b>{str(row['spc_common']).title()}</b> ({row['pct']}%)</p>" for _, row in best_trees.iterrows()])
        return f"This neighborhood is classified as <b>{status} (Correlation of {corr_val})</b>.<br><br><b>Thriving local species:</b>{advice_list}"

    resilience_info = resilient_species.groupby('NTACode').apply(get_resilience_advice, city_avg=CITY_AVG_HEALTH, include_groups=False).reset_index(name='dynamic_rx')

    final_stats = merged.groupby('NTACode', as_index=False).agg({
        'NTAName': 'first',
        'BoroName': 'first',
        'total_zip_trees': 'mean'
    })
    
    final = final_stats.merge(nta_corrs, on='NTACode', how='left')
    final = final.merge(species_info, on='NTACode', how='left')
    final = final.merge(resilience_info, on='NTACode', how='left')
    final['dynamic_rx'] = final['dynamic_rx'].fillna("High diversity area. See mix above.")
    final = final.drop_duplicates(subset=['NTACode'])
    
    return final

# --- 2. MAP GENERATION ---
def create_map(df):
    m = folium.Map(location=[40.7128, -73.9352], zoom_start=11, tiles="CartoDB positron")
    geojson_path = os.path.join(base_dir, 'data', '2020_Neighborhood_Tabulation_Areas_(NTAs)_20260414.geojson')
    with open(geojson_path, 'r') as f:
        nyc_geojson = json.load(f)

    data_dict = df.set_index('NTACode').to_dict('index')

    # INVERTED COLORS: Green for 0/Negative (Equality), Red for High Positive (Vulnerability)
    colormap = branca.colormap.LinearColormap(
        colors=['#1a9850', '#66bd63', '#d9ef8b', '#fee08b', '#f46d43', '#d73027'],
        vmin=-0.5, vmax=0.5,
        caption='Neighborhood Vulnerability (High = Health relies on Wealth)'
    )
    
    legend_css = """
    <style>
        .leaflet-control.branca-legend { 
            background: white !important; 
            padding: 10px !important; 
            border: 2px solid #333 !important; 
            border-radius: 8px !important;
            box-shadow: 0 0 10px rgba(0,0,0,0.2);
        }
    </style>
    """
    m.get_root().header.add_child(folium.Element(legend_css))
    colormap.add_to(m)

    for feature in nyc_geojson['features']:
        feature['properties'] = {k.replace(':', ''): v for k, v in feature['properties'].items()}
        nta_id = feature['properties'].get('nta2020')
        f_data = data_dict.get(nta_id)
        
        if f_data:
            local_corr = f_data.get('NTA_Correlation', 0)
            feature['properties']['viz_val'] = local_corr
            feature['properties']['trees'] = f_data.get('tree_list', "No data.")
            feature['properties']['zip_total'] = int(f_data.get('total_zip_trees', 0))
            feature['properties']['rx'] = f_data.get('dynamic_rx')
            feature['properties']['has_data'] = True
            feature['properties']['hover'] = f"<strong>{f_data['NTAName']}</strong><br>Vulnerability Score: {round(local_corr, 3)}"
        else:
            feature['properties']['has_data'] = False
            feature['properties']['viz_val'] = None
            feature['properties']['hover'] = f"<strong>{feature['properties'].get('ntaname')}</strong> (No Data)"

    def style_fn(f):
        return {
            'fillColor': colormap(f['properties']['viz_val']) if f['properties']['has_data'] else '#eeeeee',
            'color': 'white', 'weight': 1, 'fillOpacity': 0.7
        }

    for feature in nyc_geojson['features']:
        box = "font-size: 11px; background: #f8f9fa; padding: 10px; border-radius: 4px; border: 1px solid #ddd; margin-bottom: 12px;"
        popup_html = f"""
        <div style="font-family: sans-serif; width: 250px;">
            <h3 style="margin: 0;"><b>{feature['properties'].get('ntaname')}</b></h3>
            <p style="font-size: 11px; color: #666; border-bottom: 1px solid #ccc; padding-bottom: 5px; margin-bottom: 10px;">
                Trees in this area: <b>{feature['properties'].get('zip_total', 'N/A')}</b>
            </p>
            <p style="font-weight: bold; margin: 0 0 4px 0; font-size: 12px;">Neighborhood Tree Mix</p>
            <div style="{box}">{feature['properties'].get('trees', 'N/A')}</div>
            <p style="font-weight: bold; margin: 0 0 4px 0; font-size: 12px;">Resilience & Analysis</p>
            <div style="{box}">{feature['properties'].get('rx', 'N/A')}</div>
        </div>
        """
        folium.GeoJson(
            feature, style_function=style_fn,
            tooltip=folium.Tooltip(feature['properties']['hover']),
            popup=folium.Popup(popup_html, max_width=280)
        ).add_to(m)

    m.save(os.path.join(template_dir, "index.html"))

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    data = run_data_pipeline()
    create_map(data)
    app.run(debug=True, use_reloader=False)