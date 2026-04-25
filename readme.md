# NYC Green Inequality Project

## Project Goal

To determine if there is a statistically significant correlation between a neighborhood's socio-economic status (Median Household Income) and the biological health and density of its public street trees. We are looking to discover if "Green Inequality" exists across the five boroughs of NYC.

## Setup & Installation

1. **Clone the repository**
2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

## Data

## Data

You need to download the following four datasets and place them in the project folder:

1. **Tree Data**:
   Source: 2015 Street Tree Census (NYC Open Data)
   - URL: https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh
   - Click "Export" and choose "CSV".
   - Note: This is a large file (~200MB). Place the .csv file into the /data directory (e.g., /data/2015_street_tree_census.csv).

2. **Income Data**:
   Source: data.census.gov
   - Search for table S1901.
   - Click Filter (on the left).
   - Go to Geography -> Zip Code Tabulation Area (Five-Digit).
   - Select "All Zip Code Tabulation Areas within New York".
   - Download the zip for "S1901 - 2024 - ACS 5-Year Estimates Subject Tables" as CSV.
   - Place the downloaded CSV into the /data directory (e.g., /data/S1901_2024_NYC_ZCTA.csv).

3. **2020 Neighborhood Tabulation Areas (NTAs) GeoJSON**:
   - Download the GeoJSON export named: 2020*Neighborhood_Tabulation_Areas*(NTAs)\_20260414.geojson (4.63 MB).
   - Place the GeoJSON into the /data directory (e.g., /data/2020_NTAs_20260414.geojson).

4. **2020 Census Tracts to 2020 NTAs and CDTA Equivalency (CSV)**:
   Source: NYC Open Data
   - URL (CSV export): https://data.cityofnewyork.us/City-Government/2020-Census-Tracts-to-2020-NTAs-and-CDTAs-Equivale/hm78-6dwm
   - Download as CSV (use the "Export" -> "CSV" option).
   - Place the CSV into the /data directory (e.g., /data/2020_census_tracts_to_ntas_cdta.csv).

Important Notes

- Street Trees Only: The tree dataset is a census of trees planted in the "Public Right of Way" (the sidewalk).
- What is Not Included:
  - Trees in private backyards.
  - Trees in private plazas (e.g., in front of Wall Street skyscrapers).
  - Trees inside public parks (e.g., Central Park or Battery Park).
- Health Scoring: For analysis, categorical health ratings are converted to numerical values: Good = 3, Fair = 2, Poor = 1.

## Important Notes

Street Trees Only: This dataset is specifically a census of trees planted in the "Public Right of Way" (the sidewalk).

What is Not Included:

- Trees in private backyards.

- Trees in private plazas (e.g., in front of Wall Street skyscrapers).

- Trees inside public parks (e.g., Central Park or Battery Park).

Health Scoring: For analysis, categorical health ratings are converted to numerical values: Good = 3, Fair = 2, Poor = 1.
