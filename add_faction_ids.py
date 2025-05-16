import pandas as pd
from pathlib import Path

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    POLITICIANS_DIR = CACHE_DIR / "politicians"
    POLITICIANS_STAGE_01 = POLITICIANS_DIR / "stage_01"
    POLITICIANS_STAGE_02 = POLITICIANS_DIR / "stage_02"

    # Create directories if they don't exist
    for directory in [DATA_DIR, CACHE_DIR, FINAL_DIR, POLITICIANS_DIR, POLITICIANS_STAGE_02]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Adding faction IDs to MPs data...")

    # Check if the input files exist
    mps_path = POLITICIANS_STAGE_01 / "mps.pkl"
    factions_path = FINAL_DIR / "factions.pkl"

    if not mps_path.exists():
        print(f"Error: MPs data file not found at {mps_path}")
        return False

    if not factions_path.exists():
        print(f"Error: Factions data file not found at {factions_path}")
        return False

    # Read input data
    factions = pd.read_pickle(factions_path)
    mps = pd.read_pickle(mps_path)

    # Add faction_id column after electoral_term column
    if "faction_id" not in mps.columns:
        mps.insert(2, "faction_id", -1)

    # Set faction_id based on institution_name
    for faction_name, faction_id in zip(factions["faction_name"], factions["id"]):
        mps.loc[mps["institution_name"] == faction_name, "faction_id"] = faction_id

    # Save the updated DataFrame
    mps.to_pickle(POLITICIANS_STAGE_02 / "mps.pkl")
    mps.to_csv(POLITICIANS_STAGE_02 / "mps.csv", index=False)

    print(f"Added faction IDs to {len(mps)} entries")
    print(f"Saved updated MPs data to: {POLITICIANS_STAGE_02 / 'mps.pkl'}")

    return True

if __name__ == "__main__":
    main()
