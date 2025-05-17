import pandas as pd
import re
import numpy as np
from pathlib import Path

# Try to import Levenshtein or rapidfuzz for string similarity
try:
    from Levenshtein import ratio as levenshtein_ratio
except ImportError:
    try:
        from rapidfuzz.distance import Levenshtein
        def levenshtein_ratio(s1, s2):
            return Levenshtein.normalized_similarity(s1, s2)
    except ImportError:
        # Fallback to a simple implementation if neither package is available
        def levenshtein_ratio(s1, s2):
            # Simple ratio calculation based on character overlap
            if not s1 or not s2:
                return 0.0
            s1_set = set(s1.lower())
            s2_set = set(s2.lower())
            return len(s1_set.intersection(s2_set)) / max(len(s1_set), len(s2_set))

def get_fuzzy_names(df, name_to_check, fuzzy_threshold=0.7):
    """Find names that are similar to the given name"""
    if "last_name" not in df.columns:
        return pd.DataFrame()
    return df.loc[
        df["last_name"].apply(lambda x: levenshtein_ratio(str(x), str(name_to_check)) >= fuzzy_threshold)
    ]

def get_possible_matches(df, **columns):
    """Returns possible matches in df with respect to specified columns."""
    result = df.copy()
    for col_name, col_value in columns.items():
        if col_name in result.columns:
            result = result.loc[result[col_name] == col_value]
    return result

def check_unique(possible_matches, col="ui"):
    """Check if the values in the specified column are unique"""
    if len(possible_matches) == 0 or col not in possible_matches.columns:
        return False
    return len(np.unique(possible_matches[col].dropna())) == 1

def set_id(df, index, possible_matches, col_set, col_check):
    """Sets the ID in column "col_set" of "df" at "index" to the value in
    "col_check" in possible_matches.
    """
    if len(possible_matches) > 0 and col_check in possible_matches.columns:
        df.at[index, col_set] = int(possible_matches[col_check].iloc[0])

def insert_politician_id_into_contributions_extended(df, politicians_term, mgs_term):
    """Match contributions to politician IDs with improved matching"""
    # Make sure we have a DataFrame
    if isinstance(df, pd.Series):
        df = pd.DataFrame([df])

    # Create a copy to avoid modifying the original
    df_matched = df.copy()

    # Add politician_id column for storing matches
    if "politician_id" not in df_matched.columns:
        df_matched.insert(1, "politician_id", -1)

    # Track match statistics
    match_count = 0
    problems = []

    # Process each contribution
    for idx, row in df_matched.iterrows():
        # Get last name
        if "last_name" not in row or not row["last_name"]:
            problems.append(f"Missing last name at index {idx}")
            continue

        last_name = str(row["last_name"]).lower().replace("ß", "ss")

        # Get first name
        first_name = []
        if "first_name" in row and row["first_name"]:
            if isinstance(row["first_name"], list):
                first_name = [n.lower().replace("ß", "ss") for n in row["first_name"] if n]
            else:
                first_name_str = str(row["first_name"]).lower().replace("ß", "ss")
                first_name = first_name_str.split() if first_name_str else []

        # Get faction ID
        faction_id = row["faction_id"] if "faction_id" in row else -1

        # Get constituency
        constituency = row["constituency"] if "constituency" in row else ""
        constituency = str(constituency).lower() if constituency else ""

        # Get academic title
        acad_title = row["acad_title"] if "acad_title" in row else []

        # Try exact last name match with politicians from this term
        matches = get_possible_matches(politicians_term, last_name=last_name)

        # If we have a unique match, use it
        if check_unique(matches):
            set_id(df_matched, idx, matches, "politician_id", "ui")
            match_count += 1
            continue

        # If multiple matches with same last name, try narrowing down with faction
        if len(matches) > 1 and faction_id >= 0:
            faction_matches = get_possible_matches(matches, faction_id=faction_id)
            if check_unique(faction_matches):
                set_id(df_matched, idx, faction_matches, "politician_id", "ui")
                match_count += 1
                continue

        # Try matching with first name parts
        if len(matches) > 1 and first_name:
            first_name_set = set(first_name)
            filtered_matches = []

            for _, pm in matches.iterrows():
                politician_first_names = pm["first_name"]
                if isinstance(politician_first_names, list):
                    politician_name_set = set(n.lower() for n in politician_first_names if n)
                else:
                    politician_name_set = set(str(politician_first_names).lower().split())

                # Check for any overlap in first names
                if not first_name_set.isdisjoint(politician_name_set):
                    filtered_matches.append(pm)

            if len(filtered_matches) == 1:
                df_matched.at[idx, "politician_id"] = int(filtered_matches[0]["ui"])
                match_count += 1
                continue

        # Try constituency matching
        if len(matches) > 1 and constituency:
            constituency_matches = []
            for _, pm in matches.iterrows():
                pol_constituency = str(pm["constituency"]).lower() if pm["constituency"] else ""
                if pol_constituency and levenshtein_ratio(pol_constituency, constituency) > 0.7:
                    constituency_matches.append(pm)

            if len(constituency_matches) == 1:
                df_matched.at[idx, "politician_id"] = int(constituency_matches[0]["ui"])
                match_count += 1
                continue

        # Try gender matching (based on academic title)
        if len(matches) > 1:
            is_female = False
            if isinstance(acad_title, list):
                is_female = any(title == "Frau" for title in acad_title)
            else:
                is_female = "Frau" in str(acad_title)

            if is_female:
                gender_matches = matches.loc[matches["gender"] == "weiblich"]
                if check_unique(gender_matches):
                    set_id(df_matched, idx, gender_matches, "politician_id", "ui")
                    match_count += 1
                    continue

        # If no exact match with politicians, try government members
        if len(matches) == 0:
            gov_matches = get_possible_matches(mgs_term, last_name=last_name)
            if check_unique(gov_matches):
                set_id(df_matched, idx, gov_matches, "politician_id", "ui")
                match_count += 1
                continue

            # Try fuzzy matching with last names
            if len(gov_matches) == 0:
                fuzzy_matches = get_fuzzy_names(politicians_term, last_name, 0.8)
                if check_unique(fuzzy_matches):
                    set_id(df_matched, idx, fuzzy_matches, "politician_id", "ui")
                    match_count += 1
                    continue

        # If still no match, record as a problem case
        problems.append(f"Could not match '{last_name}, {first_name}' at index {idx}")

    match_percentage = (match_count / len(df_matched)) * 100 if len(df_matched) > 0 else 0
    print(f"Matched {match_count} of {len(df_matched)} entries ({match_percentage:.1f}%)")

    return df_matched, problems

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    CONTRIBUTIONS_EXTENDED_DIR = CACHE_DIR / "contributions_extended"
    CONTRIBUTIONS_EXTENDED_STAGE_02 = CONTRIBUTIONS_EXTENDED_DIR / "stage_02"
    CONTRIBUTIONS_EXTENDED_STAGE_03 = CONTRIBUTIONS_EXTENDED_DIR / "stage_03"

    # Create directories if they don't exist
    for directory in [
        DATA_DIR, CACHE_DIR, FINAL_DIR,
        CONTRIBUTIONS_EXTENDED_DIR, CONTRIBUTIONS_EXTENDED_STAGE_02, CONTRIBUTIONS_EXTENDED_STAGE_03
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Matching contributions to politicians...")

    # Load politician data
    politicians_path = FINAL_DIR / "politicians.csv"
    if not politicians_path.exists():
        print("Error: Politicians data not found. Run the previous scripts first.")
        return False

    # Load and prepare politicians data
    politicians = pd.read_csv(politicians_path)
    politicians = politicians.loc[
        :,
        [
            "ui",
            "electoral_term",
            "faction_id",
            "first_name",
            "last_name",
            "gender",
            "constituency",
            "institution_type",
        ],
    ].copy()

    # Convert data types
    politicians = politicians.astype(dtype={"ui": "int64"})

    # Clean and prepare data for matching
    politicians["constituency"] = politicians["constituency"].fillna("")

    politicians["first_name"] = politicians["first_name"].str.lower()
    politicians["last_name"] = politicians["last_name"].str.lower()
    politicians["constituency"] = politicians["constituency"].str.lower()

    politicians["first_name"] = politicians["first_name"].str.replace("ß", "ss", regex=False)
    politicians["last_name"] = politicians["last_name"].str.replace("ß", "ss", regex=False)

    politicians["first_name"] = politicians["first_name"].apply(
        lambda x: x.split() if isinstance(x, str) else []
    )

    # Process each electoral term folder
    term_count = 0
    successful_term_count = 0

    for folder_path in sorted(CONTRIBUTIONS_EXTENDED_STAGE_02.glob("electoral_term_*")):
        if not folder_path.is_dir():
            continue

        term_number = re.search(r"(?<=electoral_term_)\d{2}", folder_path.stem)
        if term_number is None:
            continue
        term_number = int(term_number.group(0))

        term_count += 1
        print(f"Matching contributions for term {term_number}...")

        # Create output directory for this term
        term_output_dir = CONTRIBUTIONS_EXTENDED_STAGE_03 / folder_path.stem
        term_output_dir.mkdir(parents=True, exist_ok=True)

        # Filter politicians for this electoral term
        politicians_term = politicians.loc[politicians["electoral_term"] == term_number]
        mgs_term = politicians_term.loc[politicians_term["institution_type"] == "Regierungsmitglied"]

        # Count files to track progress
        file_count = len(list(folder_path.glob("*.pkl")))
        processed_count = 0
        total_contributions = 0
        matched_contributions = 0

        # Process each contributions file in this term
        for contrib_file in folder_path.glob("*.pkl"):
            try:
                # Read the contributions data
                data = pd.read_pickle(contrib_file)

                # Check if the data is valid
                if data is None or len(data) == 0:
                    print(f"  Warning: Empty data in {contrib_file.name}")
                    continue

                # Check if the loaded data is a DataFrame
                if not isinstance(data, pd.DataFrame):
                    print(f"  Converting {type(data)} to DataFrame for {contrib_file.name}")
                    if isinstance(data, pd.Series):
                        # Convert Series to DataFrame
                        contributions = pd.DataFrame([data])
                    else:
                        print(f"  Error: Unable to process {contrib_file.name} - unexpected data type: {type(data)}")
                        continue
                else:
                    contributions = data

                # Match contributions to politicians
                contributions_matched, problems = insert_politician_id_into_contributions_extended(
                    contributions, politicians_term, mgs_term
                )

                # Update counts
                file_contributions = len(contributions)
                file_matches = (contributions_matched["politician_id"] != -1).sum()
                total_contributions += file_contributions
                matched_contributions += file_matches

                # Save the matched contributions
                contributions_matched.to_pickle(term_output_dir / contrib_file.name)

                processed_count += 1
                if processed_count % 10 == 0 or processed_count == file_count:
                    print(f"  Processed {processed_count}/{file_count} files, " +
                          f"matched {file_matches}/{file_contributions} in this file " +
                          f"({(file_matches/file_contributions*100):.1f}%)")

            except Exception as e:
                print(f"  Error processing {contrib_file.name}: {e}")

        if processed_count > 0:
            successful_term_count += 1
            match_percentage = (matched_contributions / total_contributions * 100) if total_contributions > 0 else 0
            print(f"Completed term {term_number}: {processed_count} files processed")
            print(f"  Matched {matched_contributions} of {total_contributions} contributions ({match_percentage:.1f}%)")

    print(f"Matched contributions for {successful_term_count} of {term_count} electoral terms")
    return True

if __name__ == "__main__":
    main()
