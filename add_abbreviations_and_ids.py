import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    FACTIONS_DIR = CACHE_DIR / "factions"
    FACTIONS_STAGE_01 = FACTIONS_DIR / "stage_01"

    # Create directories if they don't exist
    for directory in [DATA_DIR, CACHE_DIR, FINAL_DIR, FACTIONS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Adding abbreviations and IDs to factions...")

    factions_file = FACTIONS_STAGE_01 / "factions.pkl"
    print(f"Looking for factions data at: {factions_file}")

    # Check if the file exists
    if not factions_file.exists():
        print(f"Error: Factions data file not found at {factions_file}")
        print("Please run create_factions.py first")
        return False

    # Read factions data
    factions = pd.read_pickle(factions_file)

    # Define abbreviations dictionary
    abbreviations_dict = {
        "Alternative für Deutschland": "AfD",
        "Deutsche Soziale Union": "DSU",
        "Fraktion Alternative für Deutschland": "AfD",
        "Fraktion Bayernpartei": "BP",
        "Fraktion Bündnis 90/Die Grünen": "Bündnis 90/Die Grünen",
        "Fraktion DIE LINKE.": "DIE LINKE.",
        "Fraktion DP/DPB (Gast)": "DP/DPB",
        "Fraktion DRP (Gast)": "DRP",
        "Fraktion Demokratische Arbeitsgemeinschaft": "DA",
        "Fraktion Deutsche Partei": "DP",
        "Fraktion Deutsche Partei Bayern": "DPB",
        "Fraktion Deutsche Partei/Deutsche Partei Bayern": "DP/DPB",
        "Fraktion Deutsche Partei/Freie Volkspartei": "DP/FVP",
        "Fraktion Deutsche Reichspartei": "DRP",
        "Fraktion Deutsche Reichspartei/Nationale Rechte": "DRP/NR",
        "Fraktion Deutsche Zentrums-Partei": "Z",
        "Fraktion Deutscher Gemeinschaftsblock der Heimatvertriebenen und Entrechteten": "BHE",
        "Fraktion Die Grünen": "Bündnis 90/Die Grünen",
        "Fraktion Die Grünen/Bündnis 90": "Bündnis 90/Die Grünen",
        "Fraktion BÜNDNIS 90/DIE GRÜNEN": "Bündnis 90/Die Grünen",
        "Fraktion Freie Volkspartei": "FVP",
        "Fraktion Föderalistische Union": "FU",
        "Fraktion Gesamtdeutscher Block / Block der Heimatvertriebenen und Entrechteten": "GB/BHE",
        "Fraktion WAV (Gast)": "WAV",
        "Fraktion Wirtschaftliche Aufbauvereinigung": "WAV",
        "Fraktion der CDU/CSU (Gast)": "CDU/CSU",
        "Fraktion der Christlich Demokratischen Union/Christlich - Sozialen Union": "CDU/CSU",
        "Fraktion der FDP (Gast)": "FDP",
        "Fraktion der Freien Demokratischen Partei": "FDP",
        "Fraktion der Kommunistischen Partei Deutschlands": "KPD",
        "Fraktion der Partei des Demokratischen Sozialismus": "PDS",
        "Fraktion der SPD (Gast)": "SPD",
        "Fraktion der Sozialdemokratischen Partei Deutschlands": "SPD",
        "Fraktionslos": "Fraktionslos",
        "Gruppe Bündnis 90/Die Grünen": "Bündnis 90/Die Grünen",
        "Gruppe BSW - Bündnis Sahra Wagenknecht - Vernunft und Gerechtigkeit": "BSW",
        "Gruppe Deutsche Partei": "DP",
        "Gruppe Die Linke": "DIE LINKE.",
        "Gruppe Kraft/Oberländer": "KO",
        "Gruppe der Partei des Demokratischen Sozialismus": "PDS",
        "Gruppe der Partei des Demokratischen Sozialismus/Linke Liste": "PDS",
        "Südschleswigscher Wählerverband": "SSW",
        "Gast": "Gast",
        "Gruppe Nationale Rechte": "NR",
    }

    # Add abbreviation column
    factions.insert(0, "abbreviation", "")
    factions["abbreviation"] = factions["faction_name"].apply(lambda x: abbreviations_dict.get(x, ""))

    # Generate IDs based on unique abbreviations
    unique_abbreviations = np.unique(factions["abbreviation"])
    faction_ids = list(range(len(unique_abbreviations)))

    # Add ID column
    factions.insert(0, "id", -1)

    # Assign IDs to factions
    for abbrev, id in zip(unique_abbreviations, faction_ids):
        factions.loc[factions["abbreviation"] == abbrev, "id"] = id

    # Save the final DataFrame
    final_pkl_path = FINAL_DIR / "factions.pkl"
    factions.to_pickle(final_pkl_path)

    # Also save as CSV for easy inspection
    final_csv_path = FINAL_DIR / "factions.csv"
    factions.to_csv(final_csv_path, index=False)

    print(f"Saved final factions data to:")
    print(f"  - {final_pkl_path}")

    return True

if __name__ == "__main__":
    main()
