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

You need to download the following two datasets and place them in the project folder:

1.  **Tree Data**:
    Source: [2015 Street Tree Census (NYC Open Data)](https://data.cityofnewyork.us/Environment/2015-Street-Tree-Census-Tree-Data/uvpi-gqnh)

    Click "Export" and choose "CSV".
    Note: This is a large file (~200MB). Place the .csv file into the /data directory.

2.  **Income Data**:
    Source: [data.census.gov](data.census.gov)

    Filters:
    - Search for table S1901.

    - Click Filter (on the left).

    - Go to Geography → Zip Code Tabulation Area (Five-Digit).

    - Select "All Zip Code Tabulation Areas within New York".

    - Download: Select the zip for S1901 - 2024 - ACS 5-Year Estimates Subject Tables. It should contain hundreds of rows (one for every Zip Code in the city).

## Important Notes

Street Trees Only: This dataset is specifically a census of trees planted in the "Public Right of Way" (the sidewalk).

What is Not Included:

- Trees in private backyards.

- Trees in private plazas (e.g., in front of Wall Street skyscrapers).

- Trees inside public parks (e.g., Central Park or Battery Park).

Health Scoring: For analysis, categorical health ratings are converted to numerical values: Good = 3, Fair = 2, Poor = 1.
