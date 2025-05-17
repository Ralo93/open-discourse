import pandas as pd
import regex as re
import numpy as np
from pathlib import Path
import sys
import os

def clean_name_headers(text, names):
    """Remove speaker names from header/footer of text"""
    if not isinstance(text, str):
        return text

    # Simple implementation to remove names from text
    for name in names:
        if len(name) > 3:  # Only remove names longer than 3 chars to avoid false positives
            text = text.replace(name, "")

    return text

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define input and output directories
    SPEECH_CONTENT_INPUT = DATA_DIR / "cache" / "speech_content" / "stage_01"
    SPEECH_CONTENT_OUTPUT = DATA_DIR / "cache" / "speech_content" / "stage_02"
    FACTIONS = DATA_DIR / "final"

    # Create directories if they don't exist
    for directory in [SPEECH_CONTENT_OUTPUT, FACTIONS]:
        directory.mkdir(parents=True, exist_ok=True)

    # Load or create factions data
    factions_path = FACTIONS / "factions.pkl"
    if not factions_path.exists():
        # If factions data doesn't exist yet, create a simple default one
        print("Creating default factions data...")
        factions = pd.DataFrame({
            'id': range(1, 9),
            'abbreviation': [
                'CDU/CSU', 'SPD', 'FDP', 'BÜNDNIS 90/DIE GRÜNEN',
                'DIE LINKE.', 'AfD', 'Fraktionslos', 'BSW'
            ]
        })
        factions.to_pickle(factions_path)
    else:
        factions = pd.read_pickle(factions_path)

    # Define faction patterns
    faction_patterns = {
        "Bündnis 90/DIE GRÜNEN": r"(?:BÜNDNIS\s*(?:90)?/?(?:\s*D[1I]E)?|Bündnis\s*90/(?:\s*D[1I]E)?)?\s*[GC]R[UÜ].?\s*[ÑN]EN?(?:/Bündnis 90)?|Bündnis 90/DIE GRÜNEN|DIE GRÜNEN|GRÜNEN",
        "CDU/CSU": r"(?:Gast|-)?(?:\s*C\s*[DSMU]\s*S?[DU]\s*(?:\s*[/,':!.-]?)*\s*(?:\s*C+\s*[DSs]?\s*[UÙ]?\s*)?)(?:-?Hosp\.|-Gast|1)? | CDU/CSU?|CSU|CDU",
        "BP": r"^BP",
        "DA": r"^DA",
        "DP": r"^DP",
        "DIE LINKE.": r"DIE LINKE|LINKE|Die Linke|Linke",
        "DPB": r"(?:^DPB)",
        "DRP": r"DRP(\-Hosp\.)?|SRP",
        "FDP": r"\s*F\.?\s*[PDO][.']?[DP]\.?|FDP",
        "Fraktionslos": r"(?:fraktionslos|Parteilos|parteilos)",
        "FU": r"^FU",
        "FVP": r"^FVP",
        "Gast": r"Gast",
        "GB/BHE": r"(?:GB[/-]\s*)?BHE(?:-DG)?",
        "KPD": r"^KPD",
        "PDS": r"(?:Gruppe\s*der\s*)?PDS(?:/(?:LL|Linke Liste))?",
        "SPD": r"\s*'?S(?:PD|DP)(?:\.|-Gast)?|SPD",
        "SSW": r"^SSW",
        "SRP": r"^SRP",
        "WAV": r"^WAV",
        "Z": r"^Z$",
        "DBP": r"^DBP$",
        "NR": r"^NR$",
        "AfD": r"AfD|Alternative für Deutschland",
        "BSW": r"BSW|Bündnis Sahra Wagenknecht",
    }

    def get_faction_abbrev(faction, patterns):
        """matches the given faction and returns an id"""
        if not faction or not isinstance(faction, str):
            return None

        # First try exact matches
        for faction_abbrev in patterns.keys():
            if faction_abbrev.lower() == faction.lower():
                return faction_abbrev

        # Then try pattern matching
        for faction_abbrev, faction_pattern in patterns.items():
            if re.search(faction_pattern, faction, re.IGNORECASE):
                return faction_abbrev
        return None

    def get_position_short_and_long(position):
        """matches the given position and returns the long and short version"""
        if position in faction_patterns.keys() or re.match(
            r"^[Bb]erichterstatter(in)?(\s|$|,|.)", position
        ):
            return (
                "Member of Parliament",
                None if position in faction_patterns.keys() else position,
            )
        elif (
            re.match(r"^[Bb]undestagspräsident(in)?(\s|$|,|.)", position)
            or re.match(r"^[Aa]lterspräsident(in)?(\s|$|,|.)", position)
            or re.match(r"^[Vv]izebundestagspräsident(in)?(\s|$|,|.)", position)
            or re.match(r"^[Ss]chriftführer(in)?(\s|$|,|.)", position)
            or position.lower()
            in [
                "präsidentin",
                "präsident",
                "präsident des deutschen bundestages",
                "präsidentin des deutschen bundestages",
                "vizepräsidentin",
                "vizepräsident",
            ]
        ):
            return "Presidium of Parliament", position
        elif (
            re.match(r"^[Bb]undespräsident(in)?(\s|$|,|.)", position)
            or re.match(r"^[Ss]taatsminister(in)?(\s|$|,|.)", position)
            or re.match(r"^[Ss]enator(in)?(\s|$|,|.)", position)
            or re.match(r"^[Pp]räsident(in)?(\s|$|,|.)", position)
            or re.match(r"^[Gg]ast", position)
        ):
            return "Guest", position
        elif re.match(r"^[Bb]undeskanzler(in)?(\s|$|,|.)", position):
            return "Chancellor", None
        elif re.match(r"^(Bundes)?[Mm]inister(in)?(\s|$|,|.)", position):
            return "Minister", position
        elif re.match(r"^([Pp]arl\s*\.\s+)?[Ss]taatssekretär(in)?(\s|$|,|.)", position):
            return "Secretary of State", position
        else:
            return "Not found", None

    # Check if folder contains session files or all_raw_speeches.pkl
    if (SPEECH_CONTENT_INPUT / "all_raw_speeches.pkl").exists():
        # Process the combined speeches file
        print("Found all_raw_speeches.pkl - processing combined file...")

        speech_content = pd.read_pickle(SPEECH_CONTENT_INPUT / "all_raw_speeches.pkl")

        # Process in batches to avoid memory issues
        batch_size = 1000
        num_batches = (len(speech_content) + batch_size - 1) // batch_size

        for batch_idx in range(num_batches):
            start_idx = batch_idx * batch_size
            end_idx = min((batch_idx + 1) * batch_size, len(speech_content))

            print(f"Processing batch {batch_idx+1}/{num_batches} (records {start_idx+1}-{end_idx})...")

            # Extract batch
            batch = speech_content.iloc[start_idx:end_idx].copy()

            # Map column names if needed
            batch['name_raw'] = batch['speaker_name']
            batch['position_raw'] = batch['party']
            batch['speech_content'] = batch['speech_text']

            # Add constituency column for compatibility
            if 'constituency' not in batch.columns:
                batch['constituency'] = ""

            # Insert columns for processed data
            batch.insert(3, "faction_id", -1)
            batch.insert(3, "position_short", "")
            batch.insert(4, "position_long", "")
            batch.insert(5, "last_name", "")
            batch.insert(6, "first_name", "")
            batch.insert(7, "acad_title", "")

            # Fill missing values
            batch = batch.fillna("")

            # Clean speaker names from text
            names = batch["name_raw"].to_list()
            batch["speech_content"] = batch["speech_content"].apply(
                clean_name_headers, args=(np.unique(names),)
            )

            # Clean name_raw column
            batch["name_raw"] = batch["name_raw"].str.replace(
                r"[^a-zA-ZÖÄÜäöüß\-]", " ", regex=True
            )

            # Remove multiple spaces
            batch["name_raw"] = batch["name_raw"].str.replace(
                r"  +", " ", regex=True
            ).str.strip()

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
                "Prof"
            ]

            # Split names and extract components
            first_last_titles = batch["name_raw"].apply(str.split)

            # Extract academic titles
            batch["acad_title"] = [
                " ".join([acad_title for acad_title in title_list if acad_title in titles])
                for title_list in first_last_titles
            ]

            # Remove titles from names
            for index, title_list in first_last_titles.items():
                first_last_titles.at[index] = [name for name in title_list if name not in titles]

            # Extract first and last names
            for index, first_last in first_last_titles.items():
                if len(first_last) == 1:
                    batch.at[index, "first_name"] = ""
                    batch.at[index, "last_name"] = first_last[0] if first_last else ""
                elif len(first_last) >= 2:
                    batch.at[index, "first_name"] = " ".join(first_last[:-1])
                    batch.at[index, "last_name"] = first_last[-1]
                else:
                    batch.at[index, "first_name"] = ""
                    batch.at[index, "last_name"] = ""

            # Determine faction and position information
            for index, position_raw in batch["position_raw"].items():
                faction_abbrev = get_faction_abbrev(str(position_raw), faction_patterns)
                (
                    batch.at[index, "position_short"],
                    batch.at[index, "position_long"],
                ) = get_position_short_and_long(
                    faction_abbrev if faction_abbrev else re.sub("\n+", " ", position_raw)
                )

                if faction_abbrev:
                    matching_factions = factions.loc[factions["abbreviation"] == faction_abbrev, "id"]
                    if not matching_factions.empty:
                        batch.at[index, "faction_id"] = int(matching_factions.iloc[0])

            # Make sure position_long is a string, not None
            batch["position_long"] = batch["position_long"].fillna("")

            # Save batch to pickle file
            output_file = SPEECH_CONTENT_OUTPUT / f"speeches_batch_{batch_idx+1:03d}.pkl"

            # Remove original raw columns before saving
            batch = batch.drop(columns=["position_raw", "name_raw", "pattern_type", "speaker_name", "party", "speech_text"])
            batch.to_pickle(output_file)

            print(f"  + Saved batch {batch_idx+1} with {len(batch)} speeches")

    else:
        # Process individual session files
        print("Processing individual session files...")

        # Find all session files
        session_files = list(SPEECH_CONTENT_INPUT.glob("*.pkl"))

        for i, speech_content_file in enumerate(session_files):
            print(f"Processing file {i+1}/{len(session_files)}: {speech_content_file.name}")

            # read the content
            try:
                speech_content = pd.read_pickle(speech_content_file)
            except Exception as e:
                print(f"Error reading {speech_content_file}: {e}")
                continue

            # Insert acad_title column and extract plain name and titles
            speech_content.insert(3, "faction_id", -1)
            speech_content.insert(3, "position_short", "")
            speech_content.insert(4, "position_long", "")
            speech_content.insert(5, "last_name", "")
            speech_content.insert(6, "first_name", "")
            speech_content.insert(7, "acad_title", "")

            # Current workaround, because some speeches seem to not be matched
            # correctly. If second stage works without mistakes (extracting the
            # speech parts), this should not be necessary anymore.
            speech_content = speech_content.fillna("")

            # Clean all the names still remaining from PDF Header
            names = speech_content["name_raw"].to_list()
            speech_content["speech_content"] = speech_content["speech_content"].apply(
                clean_name_headers, args=(np.unique(names),)
            )

            speech_content.reset_index(inplace=True, drop=True)

            # Delete all non-alphabetical chars, keep "-" as it occurs often in names
            speech_content["name_raw"] = speech_content["name_raw"].str.replace(
                r"[^a-zA-ZÖÄÜäöüß\-]", " ", regex=True
            )

            # Replace more than two whitespaces with one
            speech_content["name_raw"] = speech_content["name_raw"].str.replace(
                r"  +", " ", regex=True
            ).str.strip()

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
                "Prof"
            ]

            # Split the name column into components at space character
            first_last_titles = speech_content["name_raw"].apply(str.split)

            # Extract acad_title, if it is in the titles list
            speech_content["acad_title"] = [
                " ".join([acad_title for acad_title in title_list if acad_title in titles])
                for title_list in first_last_titles
            ]

            # Remove titles from the first_last_name list
            for index, title_list in first_last_titles.items():
                first_last_titles.at[index] = [name for name in title_list if name not in titles]

            # Get the first and last name based on the amount of elements
            for index, first_last in first_last_titles.items():
                if len(first_last) == 1:
                    speech_content.at[index, "first_name"] = ""
                    speech_content.at[index, "last_name"] = first_last[0] if first_last else ""
                elif len(first_last) >= 2:
                    speech_content.at[index, "first_name"] = " ".join(first_last[:-1])
                    speech_content.at[index, "last_name"] = first_last[-1]
                else:
                    speech_content.at[index, "first_name"] = ""
                    speech_content.at[index, "last_name"] = ""

            # Look for factions in the position_raw column
            for index, position_raw in speech_content["position_raw"].items():
                faction_abbrev = get_faction_abbrev(str(position_raw), faction_patterns)
                (
                    speech_content.at[index, "position_short"],
                    speech_content.at[index, "position_long"],
                ) = get_position_short_and_long(
                    faction_abbrev if faction_abbrev else re.sub("\n+", " ", position_raw)
                )

                if faction_abbrev:
                    matching_factions = factions.loc[factions["abbreviation"] == faction_abbrev, "id"]
                    if not matching_factions.empty:
                        speech_content.at[index, "faction_id"] = int(matching_factions.iloc[0])

            # Make sure position_long is a string, not None
            speech_content["position_long"] = speech_content["position_long"].fillna("")

            # Save processed file
            output_file = SPEECH_CONTENT_OUTPUT / speech_content_file.name

            # Remove original raw columns before saving
            speech_content = speech_content.drop(columns=["position_raw", "name_raw"])
            speech_content.to_pickle(output_file)

            print(f"  + Processed and saved {len(speech_content)} speeches from {speech_content_file.name}")

    print("Processing complete!")
    return True

if __name__ == "__main__":
    main()
