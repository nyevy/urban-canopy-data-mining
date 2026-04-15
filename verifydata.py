import pandas as pd

# Load
trees = pd.read_csv('data/2015_Street_Tree_Census_-_Tree_Data_20260315.csv')
nta_map = pd.read_csv('data/2020_Census_Tracts_to_2020_NTAs_and_CDTAs_Equivalency_20260414.csv')

def standardize_tract(val):
    try:
        # Convert to string, remove decimal
        s = str(int(float(val)))
        # If it's a short code (like 739), pad it to 6 digits (073900)
        # Most NYC street tree tracts are stored as (Tract * 100) or just the ID
        if len(s) <= 4:
            return s.zfill(4) + "00"
        return s.zfill(6)
    except:
        return "ERROR"

trees['CT_Standard'] = trees['census tract'].apply(standardize_tract)
nta_map['CT_Standard'] = nta_map['CT2020'].apply(standardize_tract)

# --- DEBUG PRINT ---
print(f"Standardized Tree Sample: {trees['CT_Standard'].head(3).tolist()}")
print(f"Standardized Map Sample: {nta_map['CT_Standard'].head(3).tolist()}")

# Join
step1 = trees.merge(nta_map[['CT_Standard', 'NTAName']], on='CT_Standard')
target = "Bedford-Stuyvesant (East)"
found = step1[step1['NTAName'] == target]

print(f"\n--- Results for {target} ---")
print(f"Trees found: {len(found)}")