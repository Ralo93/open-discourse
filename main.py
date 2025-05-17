import os
import subprocess
from pathlib import Path

def main():
    # Create base directories
    DATA_DIR = Path("./data")
    DATA_DIR.mkdir(exist_ok=True)

    print("Starting Bundestag data processing pipeline...")
    print(f"Working directory: {Path.cwd()}")
    print(f"Data directory: {DATA_DIR.absolute()}")

    # Define scripts to run
    scripts = [

       # "download_data.py",
      # "process_xml.py"
       # "process_mp_data.py"          # Process MP data from XML
       #"scrape_government_members.py", # Scrape government members from Wikipedia

      #  "create_factions.py",          # Create factions list
      #  "add_abbreviations_and_ids.py", # Add abbreviations to factions
      #  "add_faction_ids.py",          # Add faction IDs to MPs
      #  "merge_government_members.py",   # Merge government members with MPs

        # Speech processing
       # "extract_speeches.py"          # Extract speeches from raw text WORKS i think but is buggy
        "clean_speeches.py"            # Clean and process speeches WORKS now, but needs a little more adjustment still. Some B90/Grünen geht nicht und CDU/CSU aiuch nicht
        #"match_speeches.py"             # Match speeches to politicians

        # Contributions processing
       #"extract_contributions.py",
       #"clean_contributions.py",
       #"match_contributions.py",

        #"finalize_data.py"
        #"export_to_sql.py"

    ]

    # Run each script in sequence
    all_successful = True
    for script in scripts:
        print(f"\n{'='*50}")
        print(f"Running {script}...")
        print(f"{'='*50}")

        # Run the script with error handling
        try:
            result = subprocess.run(["python", script], capture_output=True, text=True)

            # Print output
            if result.stdout:
                print(result.stdout.strip())

            # Check for errors
            if result.stderr:
                print(f"Errors:\n{result.stderr}")
                if result.returncode != 0:
                    print(f"Script {script} failed with return code {result.returncode}. Stopping pipeline.")
                    all_successful = False
                    break
                else:
                    print(f"Script {script} completed with warnings.")
            else:
                print(f"Script {script} completed successfully.")

        except Exception as e:
            print(f"Error executing {script}: {e}")
            all_successful = False
            break

    # Print final status
    print("\n" + "="*50)
    if all_successful:
        print("Processing pipeline completed successfully!")
        print(f"All data files are available in {DATA_DIR.absolute()} and its subdirectories.")
    else:
        print("Processing pipeline terminated with errors.")
    print("="*50)

if __name__ == "__main__":
    main()
