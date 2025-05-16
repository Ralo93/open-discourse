import xml.etree.ElementTree as et
import pandas as pd
from pathlib import Path
from datetime import datetime

# Define standard directories
DATA_DIR = Path("./data")
MP_BASE_DATA_DIR = DATA_DIR / "MP_BASE_DATA"
OUTPUT_DIR = DATA_DIR / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Process MPs data
print("Processing MPs data...", end="", flush=True)

# Find the XML file in the MP_BASE_DATA directory
mp_xml_file = next(MP_BASE_DATA_DIR.glob("*.xml"))
tree = et.parse(mp_xml_file)
root = tree.getroot()

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
for mdb in tree.iter("MDB"):
    ui = mdb.findtext("ID")

    # Biographical data
    birth_date = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSDATUM")
    birth_place = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSORT")
    birth_country = mdb.findtext("BIOGRAFISCHE_ANGABEN/GEBURTSLAND") or "Deutschland"
    death_date = mdb.findtext("BIOGRAFISCHE_ANGABEN/STERBEDATUM") or "-1"
    gender = mdb.findtext("BIOGRAFISCHE_ANGABEN/GESCHLECHT")
    profession = mdb.findtext("BIOGRAFISCHE_ANGABEN/BERUF")

    # Process each name entry
    for name in mdb.findall("./NAMEN/NAME"):
        first_name = name.findtext("VORNAME")
        last_name = name.findtext("NACHNAME")
        constituency = name.findtext("ORTSZUSATZ") or ""
        aristocracy = name.findtext("ADEL") or ""
        academic_title = name.findtext("AKAD_TITEL") or ""

        # Process each electoral term
        for electoral_term in mdb.findall("./WAHLPERIODEN/WAHLPERIODE"):
            electoral_term_number = electoral_term.findtext("WP")

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

# Create a DataFrame and clean up
mps_df = pd.DataFrame(mps)
mps_df["constituency"] = mps_df["constituency"].str.replace("[)(]", "", regex=True)
mps_df = mps_df.astype(dtype={"ui": "int64", "birth_date": "str", "death_date": "str"})

# Save the DataFrame
mps_df.to_pickle(OUTPUT_DIR / "mps.pkl")
mps_df.to_csv(OUTPUT_DIR / "mps.csv", index=False)
print("Done.")

# Create electoral terms data
print("Creating electoral terms data...", end="", flush=True)

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

# Convert dates to seconds since epoch
ref_date = datetime(year=1970, month=1, day=1)
for i, term in enumerate(electoral_terms):
    start = datetime.strptime(term["start_date"], "%Y-%m-%d")
    end = datetime.strptime(term["end_date"], "%Y-%m-%d")
    term["start_seconds"] = (start - ref_date).total_seconds()
    term["end_seconds"] = (end - ref_date).total_seconds()
    term["id"] = i + 1

# Save electoral terms
electoral_terms_df = pd.DataFrame(electoral_terms)
electoral_terms_df.to_csv(OUTPUT_DIR / "electoral_terms.csv", index=False)
print("Done.")
