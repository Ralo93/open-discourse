import pandas as pd
import numpy as np
import regex
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
    for directory in [DATA_DIR, CACHE_DIR, FINAL_DIR, POLITICIANS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Merging government members with MPs data...")

    # Check if the input files exist
    mgs_path = POLITICIANS_STAGE_01 / "mgs.pkl"
    mps_path = POLITICIANS_STAGE_02 / "mps.pkl"
    factions_path = FINAL_DIR / "factions.pkl"

    if not mgs_path.exists():
        print(f"Error: Government members data file not found at {mgs_path}")
        return False

    if not mps_path.exists():
        print(f"Error: MPs data file not found at {mps_path}")
        return False

    if not factions_path.exists():
        print(f"Error: Factions data file not found at {factions_path}")
        return False

    # Read input data
    mps = pd.read_pickle(mps_path)
    mgs = pd.read_pickle(mgs_path)
    factions = pd.read_pickle(factions_path)

    # Define election years for mapping to electoral terms
    electoral_terms_dict = {
        "from": [
            1949, 1953, 1957, 1961, 1965, 1969, 1972, 1976, 1980, 1983,
            1987, 1990, 1994, 1998, 2002, 2005, 2009, 2013, 2017,
        ],
        "until": [
            1953, 1957, 1961, 1965, 1969, 1972, 1976, 1980, 1983, 1987,
            1990, 1994, 1998, 2002, 2005, 2009, 2013, 2017, -1,
        ],
    }

    # Define faction patterns for matching
    faction_patterns = {
        "Bündnis 90/Die Grünen": r"(?:BÜNDNIS\s*(?:90)?/?(?:\s*D[1I]E)?|Bündnis\s*90/(?:\s*D[1I]E)?)?\s*[GC]R[UÜ].?\s*[ÑN]EN?(?:/Bündnis 90)?|Bündnis 90/Die Grünen",
        "CDU/CSU": r"(?:Gast|-)?(?:\s*C\s*[DSMU]\s*S?[DU]\s*(?:\s*[/,':!.-]?)*\s*(?:\s*C+\s*[DSs]?\s*[UÙ]?\s*)?)(?:-?Hosp\.|-Gast|1)?",
        "BP": r"^BP",
        "DA": r"^DA",
        "DP": r"^DP",
        "DIE LINKE.": r"DIE LINKE",
        "DPB": r"(?:^DPB)",
        "DRP": r"DRP(\-Hosp\.)?|SRP",
        "DSU": r"^DSU",
        "FDP": r"\s*F\.?\s*[PDO][.']?[DP]\.?",
        "Fraktionslos": r"(?:fraktionslos|Parteilos|parteilos)",
        "FU": r"^FU",
        "FVP": r"^FVP",
        "Gast": r"Gast",
        "GB/BHE": r"(?:GB[/-]\s*)?BHE(?:-DG)?",
        "KPD": r"^KPD",
        "PDS": r"(?:Gruppe\s*der\s*)?PDS(?:/(?:LL|Linke Liste))?",
        "SPD": r"\s*'?S(?:PD|DP)(?:\.|-Gast)?",
        "SSW": r"^SSW",
        "SRP": r"^SRP",
        "WAV": r"^WAV",
        "Z": r"^Z$",
        "DBP": r"^DBP$",
        "NR": r"^NR$",
    }

    # Function to match faction abbreviation
    def get_faction_abbrev(faction, patterns):
        for faction_abbrev, faction_pattern in patterns.items():
            if regex.search(faction_pattern, faction):
                return faction_abbrev
        return None

    # Function to get electoral term from years
    def get_electoral_term(from_year=None, to_year=None):
        if not from_year and not to_year:
            return None
        elif not from_year:
            if to_year in electoral_terms_dict["until"]:
                return electoral_terms_dict["until"].index(to_year) + 1
            elif to_year > 2017:
                return 19
            else:
                for counter, year in enumerate(electoral_terms_dict["until"]):
                    if year > to_year:
                        return counter + 1
        elif not to_year:
            if from_year in electoral_terms_dict["from"]:
                return electoral_terms_dict["from"].index(from_year) + 1
            elif from_year > 2017:
                return 19
            else:
                for counter, year in enumerate(electoral_terms_dict["from"]):
                    if year > from_year:
                        return counter
        else:
            from_term = get_electoral_term(from_year=from_year, to_year=None)
            to_term = get_electoral_term(from_year=None, to_year=to_year)
            if from_term and to_term and from_term != to_term:
                return list(range(from_term, to_term + 1))
            elif from_term:
                return [from_term]
        return None

    # Make a copy of MPs data for adding government members
    politicians = mps.copy()

    # Clean up first names for better matching
    politicians["first_name"] = politicians["first_name"].str.replace("-", " ", regex=False)

    # Process each government member
    success_counter = 0
    new_entries_counter = 0

    print(f"Processing {len(mgs)} government member entries...")

    for index, row in mgs.iterrows():
        last_name = row["last_name"]
        first_name = row["first_name"]
        birth_date = row["birth_date"]
        death_date = row["death_date"]
        position = row["position"]
        position_from = row["position_from"]
        position_until = row["position_until"]
        faction = row["faction"]

        # Apply hardcoded special cases for name matching
        if last_name == "Fischer" and first_name[0] == "Joschka":
            first_name = ["Joseph"]
        elif last_name == "Waigel" and first_name[0] == "Theo":
            first_name = ["Theodor"]
        elif last_name == "Baum" and first_name[0] == "Gerhart":
            first_name = ["Gerhart Rudolf"]
        elif last_name == "Heinemann" and first_name[0] == "Gustav":
            first_name = ["Gustav W."]
        elif last_name == "Lehr" and first_name[0] == "Ursula":
            first_name = ["Ursula Maria"]
        elif last_name == "Möllemann" and first_name[0] == "Jürgen":
            first_name = ["Jürgen W."]
        elif last_name == "Kinkel" and first_name[0] == "Klaus":
            faction = "FDP"

        # Get faction ID from abbreviation
        faction_abbrev = get_faction_abbrev(faction, faction_patterns)
        if faction_abbrev:
            matching_factions = factions.loc[factions["abbreviation"] == faction_abbrev, "id"]
            if not matching_factions.empty:
                faction_match = int(matching_factions.iloc[0])
            else:
                faction_match = -1
        else:
            faction_match = -1

        # Clean hyphens in first names
        first_name = [name.replace("-", " ") for name in first_name]

        # Get electoral terms for the position
        try:
            electoral_terms = get_electoral_term(
                from_year=int(position_from), to_year=int(position_until)
            )
            if not electoral_terms:
                print(f"Warning: Could not determine electoral term for {' '.join(first_name)} {last_name}")
                continue
        except Exception as e:
            print(f"Error determining electoral term for {' '.join(first_name)} {last_name}: {e}")
            continue

        # Try to find a match in MPs data
        found_match = False

        # First attempt - match on last name, first name (first word), and birth date
        possible_matches = politicians.loc[
            (politicians["last_name"] == last_name) &
            (politicians["first_name"].str.contains(first_name[0])) &
            (politicians["birth_date"].str.contains(str(birth_date)))
        ].drop_duplicates(subset="ui", keep="first")

        # If first attempt fails and we have multiple first names, try matching with full first name
        if len(possible_matches) == 0 and len(first_name) > 1:
            possible_matches = politicians.loc[
                (politicians["last_name"] == last_name) &
                (politicians["first_name"] == (" ".join([first_name[0], first_name[1]]))) &
                (politicians["birth_date"].str.contains(str(birth_date)))
            ].drop_duplicates(subset="ui", keep="first")

        # Add entry for each electoral term
        if len(possible_matches) == 1:
            found_match = True
            mp_data = possible_matches.iloc[0]
            for electoral_term in electoral_terms:
                new_row = mp_data.copy()
                new_row["electoral_term"] = electoral_term
                new_row["faction_id"] = faction_match
                new_row["institution_type"] = "Regierungsmitglied"
                new_row["institution_name"] = position

                # Add new row to the DataFrame
                politicians = pd.concat([politicians, pd.DataFrame([new_row])], ignore_index=True)
                success_counter += 1

        # If no match found, create a new entry
        if not found_match:
            ui_temp = int(politicians["ui"].max()) + 1
            for electoral_term in electoral_terms:
                new_row = {
                    "ui": ui_temp,
                    "electoral_term": electoral_term,
                    "faction_id": faction_match,
                    "first_name": " ".join(first_name),
                    "last_name": last_name,
                    "birth_place": "",
                    "birth_country": "",
                    "birth_date": str(birth_date),
                    "death_date": str(death_date),
                    "gender": "",
                    "profession": "",
                    "constituency": "",
                    "aristocracy": "",
                    "academic_title": "",
                    "institution_type": "Regierungsmitglied",
                    "institution_name": position,
                }
                politicians = pd.concat([politicians, pd.DataFrame([new_row])], ignore_index=True)
                new_entries_counter += 1

    # Save the final politicians data
    politicians.to_csv(FINAL_DIR / "politicians.csv", index=False)
    politicians.to_pickle(FINAL_DIR / "politicians.pkl")

    print(f"Merged {success_counter} government positions with existing MPs")
    print(f"Added {new_entries_counter} new entries for government members not in MPs data")
    print(f"Saved combined politicians data to: {FINAL_DIR / 'politicians.csv'}")

    return True

if __name__ == "__main__":
    main()
