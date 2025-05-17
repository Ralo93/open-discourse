import pandas as pd
import re
import numpy as np
from pathlib import Path

def clean_name_headers(text, names, remove_all=False):
    """Remove speaker names from text"""
    if not isinstance(text, str):
        return text

    # Simple implementation to remove names from text
    for name in names:
        if not name or len(str(name)) <= 3:  # Skip very short names to avoid false positives
            continue

        name_str = str(name).strip()
        if remove_all:
            text = text.replace(name_str, "")
        else:
            # Replace only at beginning or end of lines
            text = re.sub(r'(^|\n)' + re.escape(name_str) + r'($|\n)', r'\1\2', text)
            text = re.sub(r'(^|\n)' + re.escape(name_str) + r':', r'\1:', text)

    return text

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    CONTRIBUTIONS_EXTENDED_DIR = CACHE_DIR / "contributions_extended"
    CONTRIBUTIONS_EXTENDED_STAGE_01 = CONTRIBUTIONS_EXTENDED_DIR / "stage_01"
    CONTRIBUTIONS_EXTENDED_STAGE_02 = CONTRIBUTIONS_EXTENDED_DIR / "stage_02"

    # Create directories if they don't exist
    for directory in [
        DATA_DIR, CACHE_DIR, FINAL_DIR,
        CONTRIBUTIONS_EXTENDED_DIR, CONTRIBUTIONS_EXTENDED_STAGE_01, CONTRIBUTIONS_EXTENDED_STAGE_02
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    # Disable pandas warnings about setting values on copies
    pd.options.mode.chained_assignment = None

    # Check if factions file exists
    factions_path = FINAL_DIR / "factions.pkl"
    if not factions_path.exists():
        print("Error: Factions data not found. Run the previous scripts first.")
        return False

    # Load factions data
    factions = pd.read_pickle(factions_path)

    print("Cleaning contributions data...")

    # Define faction patterns for matching
    faction_patterns = {
        "Bündnis 90/Die Grünen": r"(?:BÜNDNIS\s*(?:90)?/?(?:\s*D[1I]E)?|Bündnis\s*90/(?:\s*D[1I]E)?)?\s*[GC]R[UÜ].?\s*[ÑN]EN?(?:/Bündnis 90)?",
        "CDU/CSU": r"(?:Gast|-)?(?:\s*C\s*[DSMU]\s*S?[DU]\s*(?:\s*[/,':!.-]?)*\s*(?:\s*C+\s*[DSs]?\s*[UÙ]?\s*)?)(?:-?Hosp\.|-Gast|1)?",
        "BP": r"^\[?BP\]?",
        "DA": r"^\[?DA\]?",
        "DP": r"^\[?DP\]?",
        "DIE LINKE.": r"DIE ?LINKE|LINKEN|\[DIE ?LINKE.\]",
        "DPB": r"^\[?DPB\]?",
        "DRP": r"\[?DRP(\-Hosp\.)?\]?|^\[?SRP\]?|^\[?DBP\]?",
        "FDP": r"\s*F\.?\s*[PDO][.']?[DP]\.?",
        "Fraktionslos": r"(?:fraktionslos|Parteilos)",
        "FU": r"^\[?FU\]?",
        "FVP": r"^\[?FVP\]?",
        "Gast": r"\[?Gast\]?",
        "GB/BHE": r"\[?(?:GB[/-]\s*)?BHE(?:-DG)?\]?",
        "KPD": r"^\[?KPD\]?",
        "NR": r"^\[?NR\]?$",
        "PDS": r"(?:Gruppe\s*der\s*)?PDS(?:/(?:LL|Linke Liste))?",
        "SPD": r"\s*'?S(?:PD|DP)(?:\.|-Gast)?",
        "SSW": r"^\[?SSW\]?",
        "SRP": r"^\[?SRP\]?",
        "WAV": r"^\[?WAV\]?",
        "Z": r"^\[?Z\]?$",
        "AfD": r"^\[?AfD\]?$",
        "DBP": r"^\[?DBP\]?$",
    }

    # Function to match faction abbreviation
    def get_faction_abbrev(faction, patterns):
        for faction_abbrev, faction_pattern in patterns.items():
            if re.search(faction_pattern, faction, re.IGNORECASE):
                return faction_abbrev
        return None

    # Process each electoral term folder
    term_count = 0
    processed_term_count = 0

    for folder_path in sorted(CONTRIBUTIONS_EXTENDED_STAGE_01.glob("electoral_term_*")):
        if not folder_path.is_dir():
            continue

        # Extract the term number
        term_number = re.search(r"(?<=electoral_term_)\d{2}", folder_path.stem)
        if term_number is None:
            continue
        term_number = int(term_number.group(0))

        term_count += 1
        print(f"Processing contributions for term {term_number}...")

        # Create output directory for this term
        term_output_dir = CONTRIBUTIONS_EXTENDED_STAGE_02 / folder_path.stem
        term_output_dir.mkdir(parents=True, exist_ok=True)

        # Count files to track progress
        file_count = len(list(folder_path.glob("*.pkl")))
        processed_count = 0

        # Process each contributions file in this term
        for contrib_file in folder_path.glob("*.pkl"):
            try:
                # Read the contributions data
                contributions_data = pd.read_pickle(contrib_file)

                # Check if we have valid data
                if contributions_data is None or len(contributions_data) == 0:
                    print(f"  Warning: Empty data in {contrib_file.name}")
                    # Save an empty DataFrame
                    pd.DataFrame(columns=[
                        "id", "type", "name_raw", "faction", "constituency",
                        "content", "text_position", "faction_id", "last_name",
                        "first_name", "acad_title"
                    ]).to_pickle(term_output_dir / contrib_file.name)
                    processed_count += 1
                    continue

                # Convert Series to DataFrame if needed
                if isinstance(contributions_data, pd.Series):
                    contributions_data = pd.DataFrame([contributions_data])

                # Create a new DataFrame to avoid any issues with views vs copies
                contributions_extended = pd.DataFrame()
                for col in contributions_data.columns:
                    contributions_extended[col] = contributions_data[col].copy()

                # Add new columns for processed data
                if "faction_id" not in contributions_extended.columns:
                    contributions_extended["faction_id"] = -1
                if "last_name" not in contributions_extended.columns:
                    contributions_extended["last_name"] = ""
                if "first_name" not in contributions_extended.columns:
                    contributions_extended["first_name"] = ""
                if "acad_title" not in contributions_extended.columns:
                    contributions_extended["acad_title"] = ""

                # Fill missing values
                contributions_extended = contributions_extended.fillna("")

                # Clean speaker names from text
                if "name_raw" in contributions_extended.columns:
                    names = contributions_extended["name_raw"].tolist()
                    contributions_extended["content"] = contributions_extended["content"].apply(
                        clean_name_headers, args=(np.unique(names), True)
                    )

                    # Clean name_raw column
                    contributions_extended["name_raw"] = contributions_extended["name_raw"].astype(str)
                    contributions_extended["name_raw"] = contributions_extended["name_raw"].str.replace(
                        r"[^a-zA-ZÖÄÜäöüß\-]", " ", regex=True
                    )

                    # Remove multiple spaces
                    contributions_extended["name_raw"] = contributions_extended["name_raw"].str.replace(
                        r"  +", " ", regex=True
                    )

                    # Define academic titles for extraction
                    titles = [
                        "Dr",
                        "Frau",
                        "D",
                        "-Ing",
                        "von",
                        "und",
                        "zu",
                        "van",
                        "de",
                        "Baron",
                        "Freiherr",
                        "Prinz",
                        "h",
                        "c",
                    ]

                    # Create lists to hold processed data
                    first_names = []
                    last_names = []
                    acad_titles = []

                    # Process each row
                    for idx, row in contributions_extended.iterrows():
                        name_raw = str(row["name_raw"]).strip()
                        if not name_raw or name_raw == "":
                            first_names.append([])
                            last_names.append("")
                            acad_titles.append([])
                            continue

                        # Split name into parts
                        name_parts = name_raw.split()

                        # Extract academic titles
                        row_acad_titles = [part for part in name_parts if part in titles]
                        acad_titles.append(row_acad_titles)

                        # Remove titles from name parts
                        name_parts = [part for part in name_parts if part not in titles]

                        # Extract first and last names
                        if len(name_parts) == 1:
                            first_names.append([])
                            last_names.append(name_parts[0])
                        elif len(name_parts) >= 2:
                            first_names.append(name_parts[:-1])
                            last_names.append(name_parts[-1])
                        else:
                            first_names.append([])
                            last_names.append("")

                    # Assign the processed data back to the DataFrame
                    contributions_extended["first_name"] = first_names
                    contributions_extended["last_name"] = last_names
                    contributions_extended["acad_title"] = acad_titles

                # Process faction information
                if "faction" in contributions_extended.columns:
                    faction_ids = []
                    factions_updated = []

                    for faction in contributions_extended["faction"]:
                        faction_str = str(faction)
                        faction_id = -1
                        faction_updated = faction_str

                        if faction_str and faction_str != "":
                            faction_abbrev = get_faction_abbrev(faction_str, faction_patterns)

                            if faction_abbrev:
                                faction_updated = faction_abbrev
                                try:
                                    matching_factions = factions.loc[factions["abbreviation"] == faction_abbrev, "id"]
                                    if not matching_factions.empty:
                                        faction_id = int(matching_factions.iloc[0])
                                except Exception as e:
                                    print(f"    Warning: Error matching faction '{faction_abbrev}': {e}")

                        faction_ids.append(faction_id)
                        factions_updated.append(faction_updated)

                    # Assign the processed data back to the DataFrame
                    contributions_extended["faction_id"] = faction_ids
                    contributions_extended["faction"] = factions_updated

                # Save the processed contributions
                contributions_extended.to_pickle(term_output_dir / contrib_file.name)

                processed_count += 1
                if processed_count % 10 == 0 or processed_count == file_count:
                    print(f"  Processed {processed_count}/{file_count} files")

            except Exception as e:
                print(f"  Error processing {contrib_file.name}: {e}")
                import traceback
                traceback.print_exc()

        if processed_count > 0:
            processed_term_count += 1
        print(f"Completed term {term_number}: {processed_count} files processed")

    print(f"Cleaned contributions for {processed_term_count} of {term_count} electoral terms")
    return True

if __name__ == "__main__":
    main()
