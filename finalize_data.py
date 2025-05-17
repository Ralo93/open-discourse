import pandas as pd
import re
import xml.etree.ElementTree as et
import time
import datetime
from pathlib import Path

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    RAW_DIR = DATA_DIR / "raw"
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    RAW_XML_DIR = RAW_DIR / "xml"

    SPEECH_CONTENT_DIR = CACHE_DIR / "speech_content"
    SPEECH_CONTENT_STAGE_04 = SPEECH_CONTENT_DIR / "stage_04"

    CONTRIBUTIONS_EXTENDED_DIR = CACHE_DIR / "contributions_extended"
    CONTRIBUTIONS_EXTENDED_STAGE_03 = CONTRIBUTIONS_EXTENDED_DIR / "stage_03"

    # Ensure output directory exists
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    print("Finalizing data...")
    print("Processing speech content...")

    # Collect all speeches from terms 1-18
    speech_content_01_18 = []
    for folder_path in sorted(SPEECH_CONTENT_STAGE_04.glob("electoral_term_*")):
        if not folder_path.is_dir():
            continue

        print(f"  Processing speeches from {folder_path.stem}...")
        for speech_content_file_path in sorted(folder_path.glob("*.pkl")):
            try:
                speech_data = pd.read_pickle(speech_content_file_path)
                speech_content_01_18.append(speech_data)
            except Exception as e:
                print(f"    Error reading {speech_content_file_path}: {e}")

    # If no speech data was found, create an empty DataFrame
    if not speech_content_01_18:
        print("  No speech content found. Creating empty DataFrame.")
        speech_content_01_18 = pd.DataFrame({
            "speech_id": [],
            "session": [],
            "first_name": [],
            "last_name": [],
            "faction_id": [],
            "position_short": [],
            "position_long": [],
            "politician_id": [],
            "speech_content": []
        })
    else:
        # Combine all speech data
        speech_content_01_18 = pd.concat(speech_content_01_18, sort=False)

    # Select and rename columns
    speech_content_01_18 = speech_content_01_18.loc[
        :,
        [
            "speech_id",
            "session",
            "first_name",
            "last_name",
            "faction_id",
            "position_short",
            "position_long",
            "politician_id",
            "speech_content",
        ],
    ]

    speech_content_01_18 = speech_content_01_18.rename(columns={"speech_id": "id"})

    # Process first names
    speech_content_01_18["first_name"] = speech_content_01_18["first_name"].apply(
        lambda x: " ".join(x) if isinstance(x, list) else x
    )

    # Create new IDs
    speech_content_01_18["id"] = list(range(len(speech_content_01_18)))

    # Clean session values
    speech_content_01_18["session"] = speech_content_01_18["session"].astype(str)
    speech_content_01_18["session"] = speech_content_01_18["session"].str.replace(
        r"\.pkl", "", regex=True
    )

    # Extract metadata from XML files
    print("Extracting metadata from XML files...")
    meta_data = {}

    for xml_file_path in sorted(RAW_XML_DIR.glob("**/*.xml")):
        try:
            tree = et.parse(xml_file_path)
            date_str = tree.find("DATUM").text
            if date_str:
                date = time.mktime(
                    datetime.datetime.strptime(date_str, "%d.%m.%Y").timetuple()
                )
                document_number = int(xml_file_path.stem)
                meta_data[document_number] = date
        except Exception as e:
            print(f"  Error extracting metadata from {xml_file_path}: {e}")

    # Add electoral term, date, and document URL columns
    speech_content_01_18.insert(1, "electoral_term", -1)
    speech_content_01_18.insert(4, "document_url", "")

    # Extract electoral term from session
    speech_content_01_18["electoral_term"] = speech_content_01_18["session"].apply(
        lambda x: str(x)[:2] if len(str(x)) >= 5 else "-1"
    )

    # Convert session to integer for metadata lookup
    speech_content_01_18["session"] = speech_content_01_18["session"].astype(int)

    # Add date from metadata
    speech_content_01_18["date"] = speech_content_01_18["session"].apply(
        lambda x: meta_data.get(x, None)
    )

    # Extract just the session number (last 3 digits)
    speech_content_01_18["session"] = speech_content_01_18["session"].apply(
        lambda x: str(x)[-3:]
    )

    # Create document URLs
    speech_content_01_18["document_url"] = speech_content_01_18.apply(
        lambda row: f"https://dip21.bundestag.de/dip21/btp/{row['electoral_term']}/{row['electoral_term']}{row['session']}.pdf",
        axis=1,
    )

    # Convert columns to appropriate types
    speech_content_01_18["session"] = speech_content_01_18["session"].astype("int32")
    speech_content_01_18["electoral_term"] = speech_content_01_18["electoral_term"].astype("int32")

    # For newer terms (19-20), we would normally combine with additional data
    # Since we don't have that in our simplified pipeline, we'll just use the data we have
    speech_content = speech_content_01_18

    # Save the final speech content
    print(f"Saving {len(speech_content)} speeches to {FINAL_DIR / 'speech_content.pkl'}")
    speech_content.to_pickle(FINAL_DIR / "speech_content.pkl")

    # Process contributions
    print("Processing contributions...")
    contributions_extended = []

    for folder_path in sorted(CONTRIBUTIONS_EXTENDED_STAGE_03.glob("electoral_term_*")):
        if not folder_path.is_dir():
            continue

        print(f"  Processing contributions from {folder_path.stem}...")
        for contrib_file_path in sorted(folder_path.glob("*.pkl")):
            try:
                contrib_data = pd.read_pickle(contrib_file_path)
                # Convert Series to DataFrame if needed
                if isinstance(contrib_data, pd.Series):
                    contrib_data = pd.DataFrame([contrib_data])
                contributions_extended.append(contrib_data)
            except Exception as e:
                print(f"    Error reading {contrib_file_path}: {e}")

    # If no contribution data was found, create an empty DataFrame
    if not contributions_extended:
        print("  No contributions found. Creating empty DataFrame.")
        contributions_extended = pd.DataFrame({
            "type": [],
            "first_name": [],
            "last_name": [],
            "faction_id": [],
            "id": [],
            "text_position": [],
            "politician_id": [],
            "content": []
        })
    else:
        # Combine all contribution data
        try:
            contributions_extended = pd.concat(contributions_extended, sort=False, ignore_index=True)
        except Exception as e:
            print(f"  Error concatenating contributions: {e}")
            # Try a more careful approach if concatenation fails
            columns = ["type", "first_name", "last_name", "faction_id", "id",
                       "text_position", "politician_id", "content"]
            empty_df = pd.DataFrame(columns=columns)
            contributions_extended = [empty_df]
            for df in contributions_extended:
                if isinstance(df, pd.DataFrame) and not df.empty:
                    # Ensure all required columns exist
                    for col in columns:
                        if col not in df.columns:
                            df[col] = None
                    # Select only the required columns
                    df = df[columns]
                    contributions_extended.append(df)
            contributions_extended = pd.concat(contributions_extended, sort=False, ignore_index=True)

    # Select and rename columns
    if not contributions_extended.empty:
        columns_to_select = [
            "type",
            "first_name",
            "last_name",
            "faction_id",
            "id",
            "text_position",
            "politician_id",
            "content",
        ]

        # Ensure all required columns exist
        for col in columns_to_select:
            if col not in contributions_extended.columns:
                contributions_extended[col] = None

        contributions_extended = contributions_extended.loc[:, columns_to_select]

        # Rename columns
        contributions_extended = contributions_extended.rename(
            columns={"id": "speech_id", "politician_id": "politician_id"}
        )

        # Add ID column
        contributions_extended.insert(0, "id", list(range(len(contributions_extended))))

        # Process first names
        contributions_extended["first_name"] = contributions_extended["first_name"].apply(
            lambda x: " ".join(x) if isinstance(x, list) else x
        )

        # Convert columns to appropriate types
        contributions_extended = contributions_extended.astype(
            {
                "id": "int64",
                "type": "object",
                "first_name": "object",
                "last_name": "object",
                "faction_id": "int32",
                "speech_id": "int32",
                "text_position": "int32",
                "politician_id": "int32",
                "content": "object",
            }
        )

    # Save the final contributions
    print(f"Saving {len(contributions_extended)} contributions to {FINAL_DIR / 'contributions_extended.pkl'}")
    contributions_extended.to_pickle(FINAL_DIR / "contributions_extended.pkl")

    print("Data finalization complete.")
    return True

if __name__ == "__main__":
    main()
