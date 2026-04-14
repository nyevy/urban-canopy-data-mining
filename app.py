import folium
from flask import Flask, render_template

app = Flask(__name__)

m = folium.Map(
    location=[40.693943, -73.885880],
    zoom_start=10,
    min_zoom=10,
    max_zoom=11,
    tiles="CartoDB positron_no_labels",
    dragging=False,
    min_lat=40.45,  
    max_lat=40.95,
    min_lon=-74.30, 
    max_lon=-73.75,
)

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

m.save("templates/index.html")

@app.route('/')
def index():
    return render_template('index.html')

app.run(debug=True)
