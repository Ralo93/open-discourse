import pandas as pd
import datetime
from pathlib import Path
import sys
import sqlalchemy

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"
    FINAL_DIR = DATA_DIR / "final"

    # Check if we should attempt database export
    try_db_export = False
    if len(sys.argv) > 1 and sys.argv[1] == '--export-to-db':
        try_db_export = True

    print("Preparing data for export...")

    # Load the required data files
    print("Loading data files...")

    # Check if files exist
    required_files = [
        FINAL_DIR / "contributions_extended.pkl",
        FINAL_DIR / "speech_content.pkl",
        FINAL_DIR / "factions.pkl",
        FINAL_DIR / "politicians.csv",
        FINAL_DIR / "electoral_terms.csv"
    ]

    missing_files = [f for f in required_files if not f.exists()]
    if missing_files:
        print("Error: The following required files are missing:")
        for f in missing_files:
            print(f"  - {f}")
        return False

    # Load electoral terms
    electoral_terms = pd.read_csv(FINAL_DIR / "electoral_terms.csv")

    # Load and preprocess politicians data
    politicians = pd.read_csv(FINAL_DIR / "politicians.csv")
    politicians = politicians.drop_duplicates(subset=["ui"], keep="first")
    politicians = politicians.drop(
        [
            "electoral_term",
            "faction_id",
            "institution_type",
            "institution_name",
            "constituency",
        ],
        axis=1,
    )

    politicians.columns = [
        "id",
        "first_name",
        "last_name",
        "birth_place",
        "birth_country",
        "birth_date",
        "death_date",
        "gender",
        "profession",
        "aristocracy",
        "academic_title",
    ]

    # Add a "not found" entry for missing politicians
    series = {
        "id": -1,
        "first_name": "Not found",
        "last_name": "",
        "birth_place": None,
        "birth_country": None,
        "birth_date": None,
        "death_date": None,
        "gender": None,
        "profession": None,
        "aristocracy": None,
        "academic_title": None,
    }

    politicians = pd.concat([politicians, pd.DataFrame([series])], ignore_index=True)

    # Define date conversion functions
    def convert_date_politicians(date):
        try:
            date = datetime.datetime.strptime(date, "%d.%m.%Y")
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            return date
        except (ValueError, TypeError):
            return None

    def convert_date_speeches(date):
        try:
            date = datetime.datetime.fromtimestamp(date)
            date = date.strftime("%Y-%m-%d %H:%M:%S")
            return date
        except (ValueError, TypeError) as e:
            print(f"Error converting date: {e}")
            return None

    # Function to check politician IDs
    def check_politicians(row):
        speaker_id = row["politician_id"]
        politician_ids = politicians["id"].tolist()
        if speaker_id not in politician_ids:
            speaker_id = -1
        return speaker_id

    # Prepare factions data
    print("Preparing factions data...")
    factions_list = [
        ["not found", "not found"],
        ["AfD", "Alternative für Deutschland"],
        ["BHE", "Block der Heimatvertriebenen und Entrechteten"],
        ["BP", "Bayernpartei"],
        ["BSW", "Bündnis Sahra Wagenknecht"],
        ["Grüne", "Bündnis 90/Die Grünen"],
        ["CDU/CSU", "Christlich Demokratische Union Deutschlands/Christlich-Soziale Union in Bayern"],
        ["DA", "Demokratische Arbeitsgemeinschaft"],
        ["DIE LINKE.", "DIE LINKE."],
        ["DP", "Deutsche Partei"],
        ["DP/DPB", "Deutsche Partei/Deutsche Partei Bayern"],
        ["DP/FVP", "Deutsche Partei/Freie Volkspartei"],
        ["DPB", "Deutsche Partei Bayern"],
        ["DRP", "Deutsche Reformpartei"],
        ["DRP/NR", "Deutsche Reichspartei/Nationale Rechte"],
        ["DSU", "Deutsche Soziale Union"],
        ["FDP", "Freie Demokratische Partei"],
        ["FU", "Föderalistische Union"],
        ["FVP", "Freie Volkspartei"],
        ["Fraktionslos", "Fraktionslos"],
        ["GB/BHE", "Gesamtdeutscher Block/Bund der Heimatvertriebenen und Entrechteten"],
        ["Gast", "Gast"],
        ["KO", "Kraft/Oberländer-Gruppe"],
        ["KPD", "Kommunistische Partei Deutschlands"],
        ["NR", "Nationale Rechte"],
        ["PDS", "Partei des Demokratischen Sozialismus"],
        ["SPD", "Sozialdemokratische Partei Deutschlands"],
        ["SSW", "Südschleswigscher Wählerverband"],
        ["WAV", "Wirtschaftliche Aufbau-Vereinigung"],
        ["Z", "Deutsche Zentrumspartei"],
    ]

    # Convert to DataFrame and add id-field
    factions_df = pd.DataFrame(
        [[idx-1, *entry] for idx, entry in enumerate(factions_list)],
        columns=["id", "abbreviation", "full_name"],
    )
    factions_df["id"] = factions_df["id"].astype(int)

    # Save standardized factions data
    factions_df.to_csv(FINAL_DIR / "factions_standardized.csv", index=False)

    # Process speeches data
    print("Processing speeches data...")
    speeches = pd.read_pickle(FINAL_DIR / "speech_content.pkl")
    speeches["date"] = speeches["date"].apply(convert_date_speeches)
    speeches = speeches.where((pd.notnull(speeches)), None)
    speeches["position_long"] = speeches["position_long"].replace([r"^\s*$"], [None], regex=True)
    speeches["politician_id"] = speeches.apply(check_politicians, axis=1)

    # Save processed speeches data
    speeches.to_csv(FINAL_DIR / "speeches_processed.csv", index=False)

    # Process contributions data
    print("Processing contributions data...")
    contributions_extended = pd.read_pickle(FINAL_DIR / "contributions_extended.pkl")
    contributions_extended = contributions_extended.where((pd.notnull(contributions_extended)), None)

    # Save processed contributions data
    contributions_extended.to_csv(FINAL_DIR / "contributions_extended_processed.csv", index=False)

    # Process simplified contributions data if available
    contributions_simplified_path = FINAL_DIR / "contributions_simplified.pkl"
    if contributions_simplified_path.exists():
        print("Processing simplified contributions...")
        contributions_simplified = pd.read_pickle(contributions_simplified_path)
        contributions_simplified = contributions_simplified.where((pd.notnull(contributions_simplified)), None)
        contributions_simplified["id"] = range(len(contributions_simplified))
        contributions_simplified.to_csv(FINAL_DIR / "contributions_simplified_processed.csv", index=False)

    # Process politicians data
    politicians = politicians.where((pd.notnull(politicians)), None)
    politicians["birth_date"] = politicians["birth_date"].apply(convert_date_politicians)
    politicians["death_date"] = politicians["death_date"].apply(convert_date_politicians)
    politicians.to_csv(FINAL_DIR / "politicians_processed.csv", index=False)

    print("Data processing complete. CSV files saved to the 'final' directory.")

    # Export to database if requested
    if try_db_export:
        try:
            from sqlalchemy import create_engine
            print("Attempting to export to database...")

            # Create database engine
            engine = create_engine("postgresql://postgres:postgres@localhost:5432/next")

            # Export data to database
            print("Exporting electoral_terms...", end="", flush=True)
            electoral_terms.to_sql(
                "electoral_terms", engine, if_exists="append", schema="open_discourse", index=False
            )
            print("Done.")

            print("Exporting politicians...", end="", flush=True)
            politicians.to_sql(
                "politicians", engine, if_exists="append", schema="open_discourse", index=False
            )
            print("Done.")

            print("Exporting factions...", end="", flush=True)
            factions_df.to_sql(
                "factions", engine, if_exists="append", schema="open_discourse", index=False
            )
            print("Done.")

            print("Exporting speeches...", end="", flush=True)
            speeches.to_sql(
                "speeches", engine, if_exists="append", schema="open_discourse", index=False
            )
            print("Done.")

            print("Exporting contributions_extended...", end="", flush=True)
            contributions_extended.to_sql(
                "contributions_extended",
                engine,
                if_exists="append",
                schema="open_discourse",
                index=False,
            )
            print("Done.")

            if contributions_simplified_path.exists():
                print("Exporting contributions_simplified...", end="", flush=True)
                contributions_simplified.to_sql(
                    "contributions_simplified",
                    engine,
                    if_exists="append",
                    schema="open_discourse",
                    index=False,
                )
                print("Done.")

            print("Database export completed successfully.")
        except ImportError:
            print("SQLAlchemy not installed. Database export skipped.")
        except Exception as e:
            print(f"Error exporting to database: {e}")

    return True

if __name__ == "__main__":
    main()
