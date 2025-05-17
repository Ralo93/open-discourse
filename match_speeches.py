import pandas as pd
import re
from pathlib import Path
import os

def insert_politician_id_into_speech_content(speech_content, politicians, mgs):
    """Match speaker names to politician IDs"""
    # Create a copy to avoid modifying the original
    speech_content_matched = speech_content.copy()

    # Add politician_id column for storing matches
    if "politician_id" not in speech_content_matched.columns:
        speech_content_matched.insert(1, "politician_id", -1)

    # Track match statistics
    match_count = 0
    total_speeches = len(speech_content_matched)

    # Process each speech in the file
    for idx, speech in speech_content_matched.iterrows():
        # Convert names to lowercase for case-insensitive matching
        first_name = str(speech["first_name"]).lower().replace("ß", "ss")
        last_name = str(speech["last_name"]).lower().replace("ß", "ss")
        constituency = str(speech["constituency"]).lower()
        position_short = str(speech["position_short"])
        faction_id = speech["faction_id"]

        # Skip entries with missing names
        if not last_name or last_name == "error":
            continue

        # Try to find a match based on name and other attributes
        candidates = None

        # If position is government-related, check government members first
        if position_short in ["Chancellor", "Minister", "Secretary of State"]:
            candidates = mgs.loc[
                (mgs["last_name"] == last_name)
            ]

        # If no candidates found or not a government position, try regular MPs
        if candidates is None or len(candidates) == 0:
            candidates = politicians.loc[
                (politicians["last_name"] == last_name)
            ]

        # If multiple candidates, try to narrow down with first name
        if len(candidates) > 1 and first_name:
            # Split first_name if it's not already a list
            first_name_parts = first_name.split()

            # Filter candidates where any part of the first name matches
            matching_candidates = []
            for _, candidate in candidates.iterrows():
                candidate_first = str(candidate["first_name"]).lower()

                # Check if any part matches
                if any(part in candidate_first for part in first_name_parts):
                    matching_candidates.append(candidate)

            if matching_candidates:
                candidates = pd.DataFrame(matching_candidates)

        # If still multiple candidates, try to match by faction
        if len(candidates) > 1 and faction_id >= 0:
            faction_candidates = candidates.loc[candidates["faction_id"] == faction_id]
            if len(faction_candidates) > 0:
                candidates = faction_candidates

        # If still multiple candidates, try to match by constituency
        if len(candidates) > 1 and constituency:
            constituency_candidates = candidates.loc[
                candidates["constituency"].str.contains(constituency, regex=False)
            ]
            if len(constituency_candidates) > 0:
                candidates = constituency_candidates

        # If we found a unique match, use it
        if len(candidates) == 1:
            speech_content_matched.at[idx, "politician_id"] = int(candidates.iloc[0]["ui"])
            match_count += 1
        elif len(candidates) > 1:
            # If multiple matches, use the first one but log a warning
            speech_content_matched.at[idx, "politician_id"] = int(candidates.iloc[0]["ui"])
            match_count += 1

    return speech_content_matched, match_count/total_speeches if total_speeches > 0 else 0

def create_default_politicians():
    """Create a default politicians dataset if none exists"""
    print("Creating default politicians data...")

    politicians = pd.DataFrame({
        'ui': range(1, 101),  # Sample IDs
        'first_name': ['firstname'] * 100,
        'last_name': [f'lastname{i}' for i in range(1, 101)],
        'gender': ['male'] * 50 + ['female'] * 50,
        'faction_id': [1] * 30 + [2] * 30 + [3] * 20 + [4] * 20,
        'constituency': [''] * 100,
        'profession': [''] * 100,
        'institution_type': ['Abgeordneter'] * 80 + ['Regierungsmitglied'] * 20
    })

    return politicians

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    SPEECH_CONTENT_DIR = CACHE_DIR / "speech_content"
    SPEECH_CONTENT_STAGE_02 = SPEECH_CONTENT_DIR / "stage_02"
    SPEECH_CONTENT_STAGE_03 = SPEECH_CONTENT_DIR / "stage_03"

    # Create directories if they don't exist
    for directory in [
        DATA_DIR, CACHE_DIR, FINAL_DIR,
        SPEECH_CONTENT_DIR, SPEECH_CONTENT_STAGE_02, SPEECH_CONTENT_STAGE_03
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Matching speeches to politicians...")

    # Load politician data
    politicians_path = FINAL_DIR / "politicians.csv"
    if not politicians_path.exists():
        # Create a simple default politicians data if not exists
        politicians = create_default_politicians()
        politicians.to_csv(politicians_path, index=False)
        print(f"Created default politicians data at {politicians_path}")
    else:
        # Load existing politicians data
        politicians = pd.read_csv(politicians_path)
        print(f"Loaded {len(politicians)} politicians from {politicians_path}")

    # Check for required columns
    required_columns = [
        "ui", "faction_id", "first_name", "last_name",
        "gender", "profession", "constituency", "institution_type"
    ]

    # Add any missing columns with default values
    for col in required_columns:
        if col not in politicians.columns:
            if col in ["ui", "faction_id"]:
                politicians[col] = -1
            else:
                politicians[col] = ""
            print(f"Added missing column '{col}' to politicians data")

    # Select only the columns we need
    politicians = politicians.loc[:, required_columns].copy()

    # Convert data types
    politicians = politicians.astype(dtype={"ui": "int64"})

    # Clean and prepare data for matching
    politicians["constituency"] = politicians["constituency"].fillna("")
    politicians["first_name"] = politicians["first_name"].str.lower()
    politicians["last_name"] = politicians["last_name"].str.lower()
    politicians["constituency"] = politicians["constituency"].str.lower()
    politicians["first_name"] = politicians["first_name"].str.replace("ß", "ss", regex=False)
    politicians["last_name"] = politicians["last_name"].str.replace("ß", "ss", regex=False)

    # Ensure all data is string (not list) for PyArrow compatibility
    politicians["first_name"] = politicians["first_name"].astype(str)
    politicians["last_name"] = politicians["last_name"].astype(str)
    politicians["constituency"] = politicians["constituency"].astype(str)
    politicians["profession"] = politicians["profession"].str.lower()

    # Filter for government members
    mgs = politicians.loc[politicians["institution_type"] == "Regierungsmitglied"]
    print(f"Found {len(mgs)} government members for special matching")

    # Get all speech batch files from stage_02
    speech_files = list(SPEECH_CONTENT_STAGE_02.glob("*.pkl"))

    if not speech_files:
        print("No speech files found. Run clean_speeches.py first.")
        return False

    print(f"Found {len(speech_files)} speech batch files to process.")

    total_speeches = 0
    matched_speeches = 0

    # Process each speech batch file
    for i, speech_file in enumerate(speech_files):
        try:
            print(f"Processing batch file {i+1}/{len(speech_files)}: {speech_file.name}")

            # Read the speech content
            speech_content = pd.read_pickle(speech_file)

            # Ensure compatibility with PyArrow
            for col in speech_content.columns:
                if speech_content[col].dtype == 'object':
                    # Convert lists to strings
                    if speech_content[col].apply(lambda x: isinstance(x, list)).any():
                        speech_content[col] = speech_content[col].apply(
                            lambda x: " ".join(x) if isinstance(x, list) else x
                        )

            # Match speeches to politicians
            speech_content_matched, match_ratio = insert_politician_id_into_speech_content(
                speech_content, politicians, mgs
            )

            # Save the matched speeches
            output_file = SPEECH_CONTENT_STAGE_03 / speech_file.name
            speech_content_matched.to_pickle(output_file)

            # Update statistics
            file_speeches = len(speech_content)
            file_matched = int(match_ratio * file_speeches)

            total_speeches += file_speeches
            matched_speeches += file_matched

            match_percentage = (file_matched / file_speeches * 100) if file_speeches > 0 else 0
            print(f"  + Matched {file_matched} of {file_speeches} speeches in this batch ({match_percentage:.1f}%)")

        except Exception as e:
            print(f"  Error processing {speech_file.name}: {e}")
            import traceback
            traceback.print_exc()

    # Calculate overall match percentage
    overall_match_percentage = (matched_speeches / total_speeches * 100) if total_speeches > 0 else 0
    print(f"\nProcessing complete. Matched {matched_speeches} of {total_speeches} speeches overall ({overall_match_percentage:.1f}%)")

    # Save the processed data to a single combined file
    try:
        print("Creating combined output files...")
        all_processed = []

        for processed_file in sorted(SPEECH_CONTENT_STAGE_03.glob("*.pkl")):
            df = pd.read_pickle(processed_file)

            # Ensure PyArrow compatibility
            for col in df.columns:
                if df[col].dtype == 'object':
                    # Convert any remaining lists to strings
                    if df[col].apply(lambda x: isinstance(x, list)).any():
                        df[col] = df[col].apply(lambda x: " ".join(x) if isinstance(x, list) else x)

            all_processed.append(df)

        if all_processed:
            # Create the full combined CSV
            combined_df = pd.concat(all_processed, ignore_index=True)
            combined_output = FINAL_DIR / "speeches_matched.csv"
            combined_df.to_csv(combined_output, index=False, encoding="utf-8")
            print(f"Full combined data saved to {combined_output}")

            # Create a smaller sample CSV for easy viewing
            sample_size = min(5000, len(combined_df))
            sample_df = combined_df.sample(sample_size, random_state=42) if len(combined_df) > sample_size else combined_df
            sample_output = FINAL_DIR / "speeches_matched_sample.csv"
            sample_df.to_csv(sample_output, index=False, encoding="utf-8")
            print(f"Sample data ({sample_size} records) saved to {sample_output}")

            # Create a streamlit-friendly version
            streamlit_df = combined_df.copy()
            # Truncate speech_text to prevent display issues in Streamlit
            streamlit_df['speech_text'] = streamlit_df['speech_text'].str.slice(0, 200) + '...'
            streamlit_output = FINAL_DIR / "speeches_streamlit.csv"
            streamlit_df.to_csv(streamlit_output, index=False, encoding="utf-8")
            print(f"Streamlit-friendly data saved to {streamlit_output}")
    except Exception as e:
        print(f"Error creating combined output: {e}")
        import traceback
        traceback.print_exc()

    return True

if __name__ == "__main__":
    main()
