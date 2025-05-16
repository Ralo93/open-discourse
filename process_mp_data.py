import pandas as pd
import xml.etree.ElementTree as et
import re
from pathlib import Path
from datetime import datetime

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories - using more accessible paths
    RAW_DIR = DATA_DIR / "raw"
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    MP_BASE_DATA_DIR = RAW_DIR / "MP_BASE_DATA"
    POLITICIANS_DIR = CACHE_DIR / "politicians"
    POLITICIANS_STAGE_01 = POLITICIANS_DIR / "stage_01"
    ELECTORAL_TERMS_DIR = FINAL_DIR

    # Create directories if they don't exist
    for directory in [DATA_DIR, RAW_DIR, CACHE_DIR, FINAL_DIR,
                     MP_BASE_DATA_DIR, POLITICIANS_DIR, POLITICIANS_STAGE_01,
                     ELECTORAL_TERMS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Processing MPs data...")

    # Check if MP_BASE_DATA exists, if not, try to find it in an alternative location
    mp_xml_files = list(MP_BASE_DATA_DIR.glob("*.xml"))

    if not mp_xml_files:
        print(f"Warning: No XML files found in {MP_BASE_DATA_DIR}")
        print("Please download the MP data file and save it to this directory")
        return False

    mp_xml_file = mp_xml_files[0]
    print(f"Using MP data file: {mp_xml_file}")

    try:
        tree = et.parse(mp_xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Error parsing XML file: {e}")
        return False

    # Create a dictionary to store MP data
    mps = {
        "ui": [],
        "electoral_term": [],
        "first_name": [],
        "last_name": [],
        "birth_place": [],
        "birth_country": [],
        "birth_date": [],
        "death_date": [],
        "gender": [],
        "profession": [],
        "constituency": [],
        "aristocracy": [],
        "academic_title": [],
        "institution_type": [],
        "institution_name": [],
    }

    # Process each MP in the XML file
    mp_count = 0
    entry_count = 0
    for mdb in root.iter("MDB"):
        mp_count += 1
        ui = mdb.findtext("ID")

        # Biographical data
        birth_date = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSDATUM") or ""
        birth_place = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSORT") or ""
        birth_country = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSLAND") or "Deutschland"
        death_date = mdb.findtext("BIOGRAFISCHE_ANGABEN/STERBEDATUM") or "-1"
        gender = mdb.findtext("BIOGRAFISCHE_ANGABEN/GESCHLECHT") or ""
        profession = mdb.findtext("BIOGRAFISCHE_ANGABEN/BERUF") or ""

        # Process each name entry
        for name in mdb.findall("./NAMEN/NAME"):
            first_name = name.findtext("VORNAME") or ""
            last_name = name.findtext("NACHNAME") or ""
            constituency = name.findtext("ORTSZUSATZ") or ""
            aristocracy = name.findtext("ADEL") or ""
            academic_title = name.findtext("AKAD_TITEL") or ""

            # Special handling for Schmidt (Weilburg)
            if re.search(r"\(Weilburg\)", last_name):
                last_name = last_name.replace(" (Weilburg)", "")
                constituency = "(Weilburg)"

            # Process each electoral term
            for electoral_term in mdb.findall("./WAHLPERIODEN/WAHLPERIODE"):
                electoral_term_number = electoral_term.findtext("WP") or ""

                # Process each institution (faction)
                for institution in electoral_term.findall("./INSTITUTIONEN/INSTITUTION"):
                    institution_name = institution.findtext("INS_LANG") or ""
                    institution_type = institution.findtext("INSART_LANG") or ""

                    # Add data to the dictionary
                    mps["ui"].append(ui)
                    mps["electoral_term"].append(electoral_term_number)
                    mps["first_name"].append(first_name)
                    mps["last_name"].append(last_name)
                    mps["birth_place"].append(birth_place)
                    mps["birth_country"].append(birth_country)
                    mps["birth_date"].append(birth_date)
                    mps["death_date"].append(death_date)
                    mps["gender"].append(gender)
                    mps["profession"].append(profession)
                    mps["constituency"].append(constituency)
                    mps["aristocracy"].append(aristocracy)
                    mps["academic_title"].append(academic_title)
                    mps["institution_type"].append(institution_type)
                    mps["institution_name"].append(institution_name)
                    entry_count += 1

        if mp_count % 100 == 0:
            print(f"Processed {mp_count} MPs...")

    print(f"Processed a total of {mp_count} MPs with {entry_count} entries")

    # Create a DataFrame and clean up
    mps_df = pd.DataFrame(mps)
    mps_df["constituency"] = mps_df["constituency"].str.replace("[)(]", "", regex=True)
    mps_df = mps_df.astype(dtype={"ui": "int64", "birth_date": "str", "death_date": "str"})

    # Save the DataFrame
    save_path = POLITICIANS_STAGE_01 / "mps.pkl"
    mps_df.to_pickle(save_path)

    # Also save as CSV for easier inspection
    csv_path = POLITICIANS_STAGE_01 / "mps.csv"
    mps_df.to_csv(csv_path, index=False)

    print(f"Saved MPs data to: {save_path}")

    # Create electoral terms data
    print("Creating electoral terms data...")

    electoral_terms = [
        {"start_date": "1949-09-07", "end_date": "1953-10-05"},
        {"start_date": "1953-10-06", "end_date": "1957-10-14"},
        {"start_date": "1957-10-15", "end_date": "1961-10-16"},
        {"start_date": "1961-10-17", "end_date": "1965-10-18"},
        {"start_date": "1965-10-19", "end_date": "1969-10-19"},
        {"start_date": "1969-10-20", "end_date": "1972-12-12"},
        {"start_date": "1972-12-13", "end_date": "1976-12-13"},
        {"start_date": "1976-12-14", "end_date": "1980-11-03"},
        {"start_date": "1980-11-04", "end_date": "1983-03-28"},
        {"start_date": "1983-03-29", "end_date": "1987-02-17"},
        {"start_date": "1987-02-18", "end_date": "1990-12-19"},
        {"start_date": "1990-12-20", "end_date": "1994-11-09"},
        {"start_date": "1994-11-10", "end_date": "1998-10-25"},
        {"start_date": "1998-10-26", "end_date": "2002-10-16"},
        {"start_date": "2002-10-17", "end_date": "2005-10-17"},
        {"start_date": "2005-10-18", "end_date": "2009-10-26"},
        {"start_date": "2009-10-27", "end_date": "2013-10-21"},
        {"start_date": "2013-10-22", "end_date": "2017-10-23"},
        {"start_date": "2017-10-24", "end_date": "2021-10-26"},
        {"start_date": "2021-10-27", "end_date": "2025-10-29"},
    ]

    # Convert dates to seconds
    ref_date = datetime(year=1970, month=1, day=1)
    for i, term in enumerate(electoral_terms):
        start = datetime.strptime(term["start_date"], "%Y-%m-%d")
        end = datetime.strptime(term["end_date"], "%Y-%m-%d")
        term["start_seconds"] = (start - ref_date).total_seconds()
        term["end_seconds"] = (end - ref_date).total_seconds()
        term["id"] = i + 1

    # Create DataFrame
    electoral_terms_df = pd.DataFrame(electoral_terms)

    # Save electoral terms
    et_save_path = ELECTORAL_TERMS_DIR / "electoral_terms.csv"
    electoral_terms_df.to_csv(et_save_path, index=False)
    print(f"Saved electoral terms to: {et_save_path}")

    return True

if __name__ == "__main__":
    main()
