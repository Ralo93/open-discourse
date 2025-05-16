import pandas as pd
import numpy as np
from pathlib import Path

def main():
    # Define the path structure similar to path_definitions.py
    ROOT_DIR = (Path(__file__) / "..").resolve()
    DATA = ROOT_DIR / "data"
    DATA_CACHE = DATA / "cache"

    # Set up the specific paths we need
    POLITICIANS = DATA_CACHE / "politicians"
    POLITICIANS_STAGE_01 = POLITICIANS / "stage_01"

    FACTIONS = DATA_CACHE / "factions"
    FACTIONS_STAGE_01 = FACTIONS / "stage_01"

    # Create directories if they don't exist
    FACTIONS_STAGE_01.mkdir(parents=True, exist_ok=True)

    print("Creating factions list...")
    print(f"Looking for MPs data at: {POLITICIANS_STAGE_01 / 'mps.pkl'}")

    # Check if the data directory exists
    if not POLITICIANS_STAGE_01.exists():
        print(f"Creating directory: {POLITICIANS_STAGE_01}")
        POLITICIANS_STAGE_01.mkdir(parents=True, exist_ok=True)

        # If we don't have the original directory, check if it exists in the simplified structure
        alt_path = Path("./data/politicians_stage_01")
        if alt_path.exists() and (alt_path / "mps.pkl").exists():
            print(f"Found MPs data in alternative location: {alt_path}")
            # Create symlink or copy file
            import shutil
            shutil.copy2(alt_path / "mps.pkl", POLITICIANS_STAGE_01 / "mps.pkl")
            print(f"Copied MPs data to the expected location: {POLITICIANS_STAGE_01 / 'mps.pkl'}")

    # Check if the file exists
    if not (POLITICIANS_STAGE_01 / "mps.pkl").exists():
        print(f"Error: MPs data file not found at {POLITICIANS_STAGE_01 / 'mps.pkl'}")
        print("Please run process_mp_data.py first or ensure the file is in the correct location")
        return False

    # Read MPs data
    try:
        mps = pd.read_pickle(POLITICIANS_STAGE_01 / "mps.pkl")
    except Exception as e:
        print(f"Error reading MPs data: {e}")
        return False

    # Extract factions
    factions = mps.loc[mps["institution_type"] == "Fraktion/Gruppe", "institution_name"]

    # Get unique factions and append additional ones
    unique_factions = np.unique(factions)
    unique_factions = np.append(
        unique_factions,
        [
            "Südschleswigscher Wählerverband",
            "Gast",
            "Gruppe Nationale Rechte",
            "Deutsche Soziale Union",
        ],
    )

    # Create DataFrame
    unique_factions = pd.DataFrame(unique_factions, columns=["faction_name"])

    # Save to file
    save_path_factions = FACTIONS_STAGE_01 / "factions.pkl"
    unique_factions.to_pickle(save_path_factions)

    # Also save as CSV for easier inspection
    csv_path = FACTIONS_STAGE_01 / "factions.csv"
    unique_factions.to_csv(csv_path, index=False)

    print(f"Saved factions list to:")
    print(f"  - {save_path_factions}")

    return True

if __name__ == "__main__":
    main()
