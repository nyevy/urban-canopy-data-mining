import pandas as pd
import folium
import json
import os
import branca
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
    inc['zip'] = inc['GEO_ID'].str.split('US').str[-1]
    
    trees = pd.read_csv(TREE_DATA)
    trees = trees[trees['status'] == 'Alive'].copy()
    trees['h_num'] = trees['health'].map({'Good': 3, 'Fair': 2, 'Poor': 1})
    trees['postcode'] = trees['postcode'].astype(str).str.strip()

    CITY_AVG_HEALTH = trees['h_num'].mean()
    zip_tree_counts = trees.groupby('postcode').size().reset_index(name='total_zip_trees')

    nta_map = pd.read_csv(NTA_MAPPING)
    def norm(v): 
        try: return str(int(float(str(v).replace(',', ''))))
        except: return None
    trees['CT_Norm'] = trees['census tract'].apply(norm)
    nta_map['CT_Norm'] = nta_map['CT2020'].apply(norm)

    merged = trees.merge(nta_map[['CT_Norm', 'NTACode', 'BoroName']], on='CT_Norm')
    merged = merged.merge(inc[['zip', 'median_income']], left_on='postcode', right_on='zip')
    merged = merged.merge(zip_tree_counts, left_on='postcode', right_on='postcode')

    # Tree Mix (Top 10 species >= 2.5%)
    species_counts = merged.groupby(['NTACode', 'spc_common']).size().reset_index(name='count')
    total_counts = merged.groupby('NTACode').size().reset_index(name='total')
    species_pct = species_counts.merge(total_counts, on='NTACode')
    species_pct['pct'] = (species_pct['count'] / species_pct['total'] * 100).round(1)
    
    def get_top_species(group):
        top = group[group['pct'] >= 2.5].sort_values(by='pct', ascending=False).head(10)
        return "".join([f"<p style='margin:2px 0;'>• <b>{str(row['spc_common']).title()}</b> ({row['pct']}% of neighborhood trees)</p>" for _, row in top.iterrows()])
    
    species_info = species_pct.groupby('NTACode').apply(get_top_species, include_groups=False).reset_index(name='tree_list')

    # Aggregated Stats for Correlation
    stats = merged.groupby(['NTACode', 'BoroName'], as_index=False).agg(
        avg_i=('median_income', 'mean'),
        avg_h=('h_num', 'mean'),
        zip_total=('total_zip_trees', 'first')
    )
    
    boros = stats.groupby('BoroName').apply(lambda x: x['avg_i'].corr(x['avg_h']) if len(x) > 1 else 0, include_groups=False).reset_index()
    boros.columns = ['BoroName', 'Boro_Correlation']
    final_stats = stats.merge(boros, on='BoroName')

    # --- DYNAMIC ADVICE WITH CORRELATION ---
    health_stats = merged.groupby(['NTACode', 'spc_common']).agg(
        avg_health=('h_num', 'mean'),
        sample_size=('h_num', 'count')
    ).reset_index()
    
    resilient_species = health_stats[health_stats['sample_size'] >= 10]
    
    # We merge the correlation back into health_stats so the group has access to it
    resilient_species = resilient_species.merge(boros, left_on=resilient_species['NTACode'].map(final_stats.set_index('NTACode')['BoroName']), right_on='BoroName')

    def get_resilience_advice(group, city_avg):
        avg_h = group['avg_health'].mean()
        status = "Non-vulnerable" if avg_h >= city_avg else "Vulnerable"
        # Access the correlation value from the first row of the group
        corr_val = round(group['Boro_Correlation'].iloc[0], 3)
        
        best_trees = group.sort_values(by='avg_health', ascending=False).head(3)
        advice_list = "".join([f"<p style='margin:2px 0;'>• <b>{str(row['spc_common']).title()}</b> (High local health rating)</p>" for _, row in best_trees.iterrows()])
        
        summary = f"This zip code is classified as <b>{status} ({corr_val})</b> based on average canopy health.<br><br><b>Least vulnerable species in this area:</b><br>{advice_list}"
        return summary

    resilience_info = resilient_species.groupby('NTACode').apply(get_resilience_advice, city_avg=CITY_AVG_HEALTH, include_groups=False).reset_index(name='dynamic_rx')

    h_min, h_max = final_stats['avg_h'].min(), final_stats['avg_h'].max()
    final_stats['color_score'] = (final_stats['avg_h'] - h_min) / (h_max - h_min) - 0.5

    final = final_stats.merge(species_info, on='NTACode', how='left')
    final = final.merge(resilience_info, on='NTACode', how='left')
    final['dynamic_rx'] = final['dynamic_rx'].fillna("This neighborhood has high species diversity, but no single species met the minimum sample size (10 trees) for a reliable resilience rating.")
    final['NTACode'] = final['NTACode'].astype(str).str.strip()
    return final

# --- 2. MAP GENERATION ---
def create_map(df):
    m = folium.Map(location=[40.7128, -73.9352], zoom_start=11, tiles="CartoDB positron")

    geojson_path = os.path.join(base_dir, 'data', '2020_Neighborhood_Tabulation_Areas_(NTAs)_20260414.geojson')
    with open(geojson_path, 'r') as f:
        nyc_geojson = json.load(f)

    data_dict = df.set_index('NTACode').to_dict('index')

    colormap = branca.colormap.LinearColormap(
        colors=['#d73027', '#f46d43', '#fee08b', '#d9ef8b', '#66bd63', '#1a9850'],
        vmin=-0.5, vmax=0.5,
        caption='Income-Tree Health Correlation (Red=Low Link, Green=High Link)'
    )
    
    # More robust CSS targeting for the legend background
    legend_css = """
    <style>
        .leaflet-control.branca-legend { 
            background: white !important; 
            padding: 10px !important; 
            border: 2px solid #555 !important; 
            border-radius: 8px !important;
            box-shadow: 2px 2px 6px rgba(0,0,0,0.3) !important;
        }
        svg.leaflet-control { background: white !important; }
    </style>
    """
    m.get_root().header.add_child(folium.Element(legend_css))
    colormap.add_to(m)

    for feature in nyc_geojson['features']:
        feature['properties'] = {k.replace(':', ''): v for k, v in feature['properties'].items()}
        nta_id = feature['properties'].get('nta2020')
        feature_data = data_dict.get(nta_id)
        
        if feature_data:
            corr = round(feature_data.get('Boro_Correlation', 0), 3)
            feature['properties']['viz_score'] = feature_data.get('color_score', 0)
            feature['properties']['trees'] = feature_data.get('tree_list', "No data.")
            feature['properties']['zip_total'] = int(feature_data.get('zip_total', 0))
            feature['properties']['rx'] = feature_data.get('dynamic_rx', "Insufficient data for resilience analysis.")
            feature['properties']['has_data'] = True
            feature['properties']['hover_info'] = f"<strong>{feature['properties']['ntaname']}</strong><br>Correlation: {corr}"
        else:
            feature['properties']['has_data'] = False
            feature['properties']['viz_score'] = None
            feature['properties']['hover_info'] = f"<strong>{feature['properties']['ntaname']}</strong><br>No Data"

    def style_fn(f):
        return {
            'fillColor': colormap(f['properties']['viz_score']) if f['properties']['has_data'] else '#D3D3D3',
            'color': 'white', 'weight': 1, 'fillOpacity': 0.7
        }

    for feature in nyc_geojson['features']:
        section_style = "font-size: 11px; background: #f2f2f2; padding: 10px; border-radius: 4px; border: 1px solid #ddd; margin-bottom: 12px; line-height: 1.4;"
        
        popup_html = f"""
        <div style="font-family: Arial; width: 250px;">
            <h3 style="margin: 0 0 5px 0; font-size: 16px;"><b>{feature['properties']['ntaname']}</b></h3>
            <p style="margin: 0 0 10px 0; font-size: 12px; color: #666; border-bottom: 2px solid #333; padding-bottom: 5px;">
                Total trees in this zip code: <b>{feature['properties'].get('zip_total', 'N/A')}</b>
            </p>
            <p style="margin: 0 5px 3px 5px; font-weight: bold; color: #444; font-size: 12px;">Current Tree Mix</p>
            <div style="{section_style}">{feature['properties'].get('trees', 'N/A')}</div>
            <p style="margin: 0 5px 3px 5px; font-weight: bold; color: #444; font-size: 12px;">Resilience & Advice</p>
            <div style="{section_style}">{feature['properties'].get('rx', 'N/A')}</div>
        </div>
        """
        folium.GeoJson(
            feature,
            style_function=style_fn,
            tooltip=folium.Tooltip(feature['properties']['hover_info']),
            popup=folium.Popup(popup_html, max_width=270)
        ).add_to(m)

    # Info Box (Interpret Data)
    info_html = """
    <div style="position: fixed; bottom: 30px; left: 30px; width: 280px; 
    background-color: white; border:2px solid #555; z-index:9999; font-size:13px;
    padding: 12px; border-radius: 8px; box-shadow: 2px 2px 10px rgba(0,0,0,0.2);">
        <details>
            <summary style="font-weight: bold; cursor: pointer; list-style: none; display: flex; justify-content: space-between;">
                How to interpret the data? <span style="font-size: 14px;">➕</span>
            </summary>
            <div style="margin-top: 10px; border-top: 1px solid #ccc; padding-top: 10px;">
                <b>Color Gradient:</b> Relationship between income and tree health.<br><br>
                <b>Green:</b> Stronger link between wealth and health.<br>
                <b>Red:</b> Weaker link between wealth and health.<br><br>
                <i>Parenthesis in Advice: Shows specific borough correlation value.</i>
            </div>
        </details>
    </div>
    """
    m.get_root().html.add_child(folium.Element(info_html))
    m.save(os.path.join(template_dir, "index.html"))

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    data = run_data_pipeline()
    create_map(data)
    app.run(debug=True, use_reloader=False)