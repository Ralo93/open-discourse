from bs4 import BeautifulSoup
import pandas as pd
import regex
import requests
from pathlib import Path

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    POLITICIANS_DIR = CACHE_DIR / "politicians"
    POLITICIANS_STAGE_01 = POLITICIANS_DIR / "stage_01"

    # Create directories if they don't exist
    for directory in [DATA_DIR, CACHE_DIR, POLITICIANS_DIR, POLITICIANS_STAGE_01]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Scraping government members data from Wikipedia...")

    URL = "https://de.wikipedia.org/wiki/Liste_der_deutschen_Regierungsmitglieder_seit_1949"

    try:
        page = requests.get(URL)
        page.raise_for_status()  # Raise exception for failed requests
        soup = BeautifulSoup(page.text, "html.parser")
        main_section = soup.find("div", {"id": "mw-content-text"}).find("div")
    except Exception as e:
        print(f"Error fetching Wikipedia page: {e}")
        return False

    # Dictionary to store government members data
    mgs = {
        "ui": [],
        "last_name": [],
        "first_name": [],
        "position": [],
        "position_from": [],
        "position_until": [],
        "birth_date": [],
        "death_date": [],
        "faction": [],
        "additional_faction": [],
    }

    ui = 0
    entries_count = 0

    for div in main_section.find_all("div", recursive=False):
        for ul in div.find_all("ul", recursive=False):
            for li in ul.find_all("li", recursive=False):
                find_all_a = li.find_all("a", recursive=False)
                if not find_all_a:
                    continue

                name = find_all_a[0].text

                if "Liste" in name or "Kabinett" in name:
                    break

                # Skip Kristine Schröder due to name change in HTML structure
                if "CDU" in name:
                    continue

                name = name.split(" ")
                first_name = name[:-1]
                last_name = name[-1]

                # Extract faction information
                if len(find_all_a) > 2:
                    faction = find_all_a[1].text
                    additional_faction = find_all_a[2].text
                elif len(find_all_a) == 2:
                    faction = find_all_a[1].text
                    additional_faction = ""
                else:
                    faction = "parteilos"
                    additional_faction = ""

                # Extract birth/death years
                birth_death = li.a.next_sibling.strip()
                match_years = regex.findall(r"(\d{4})", birth_death)
                if len(match_years) == 1:
                    birth_date = int(match_years[0])
                    death_date = -1
                elif len(match_years) == 2:
                    birth_date = int(match_years[0])
                    death_date = int(match_years[1])
                else:
                    birth_date = -1
                    death_date = -1

                # Process government positions
                positions_processed = 0
                for pos in li.find_all("li"):
                    positions_processed += 1
                    pos_text = pos.text
                    match_years = regex.findall(r"(\d{4})", pos_text)

                    # Different cases based on the format of the position text
                    if len(match_years) == 2:
                        # Example: "1974–1980 Verkehr und Post- und Fernmeldewesen"
                        position_from = int(match_years[0])
                        position_until = int(match_years[1])
                        position_full = pos_text.split(" ", 1)
                        if len(position_full) == 2:
                            position = position_full[1]
                        else:
                            print(f"Warning: Can't determine position for {' '.join(first_name)} {last_name}")
                            continue

                    elif len(match_years) == 1:
                        if "seit" in pos_text:
                            # Example: "seit 2018 Arbeit und Soziales"
                            position_from = int(match_years[0])
                            position_until = -1
                            pos_text = pos_text.split(" ", 1)[1]
                            pos_text = pos_text.split(" ", 1)
                            position = pos_text[1]
                        else:
                            # Example: "1969 Justiz"
                            pos_text = pos_text.split(" ", 1)
                            if len(pos_text) > 1:
                                position = pos_text[1]
                                position_from = position_until = int(match_years[0])
                            else:
                                print(f"Warning: Invalid position format for {' '.join(first_name)} {last_name}")
                                continue

                    elif len(match_years) == 4:
                        # Example: "1969–1982, 1982–1983 Keks Beauftragter"
                        parts = pos_text.split(" ", 1)
                        if len(parts) > 1:
                            position = parts[1].split(" ", 1)[1]
                            position_from = int(match_years[0])
                            position_until = int(match_years[1])

                            # Add first position
                            mgs["ui"].append(f"gov_{ui}")
                            mgs["first_name"].append(first_name)
                            mgs["last_name"].append(last_name)
                            mgs["position"].append(position)
                            mgs["position_from"].append(position_from)
                            mgs["position_until"].append(position_until)
                            mgs["birth_date"].append(birth_date)
                            mgs["death_date"].append(death_date)
                            mgs["faction"].append(faction)
                            mgs["additional_faction"].append(additional_faction)
                            entries_count += 1

                            # Update dates for second position
                            position_from = int(match_years[2])
                            position_until = int(match_years[3])
                        else:
                            print(f"Warning: Invalid position format for {' '.join(first_name)} {last_name}")
                            continue
                    else:
                        print(f"Warning: Skipping position with unusual year format for {' '.join(first_name)} {last_name}")
                        continue

                    # Add the position entry
                    mgs["ui"].append(f"gov_{ui}")
                    mgs["first_name"].append(first_name)
                    mgs["last_name"].append(last_name)
                    mgs["position"].append(position)
                    mgs["position_from"].append(position_from)
                    mgs["position_until"].append(position_until)
                    mgs["birth_date"].append(birth_date)
                    mgs["death_date"].append(death_date)
                    mgs["faction"].append(faction)
                    mgs["additional_faction"].append(additional_faction)
                    entries_count += 1

                # Only increment UI counter if we processed positions
                if positions_processed > 0:
                    ui += 1

    # Create and save DataFrame
    mgs_df = pd.DataFrame(mgs)
    save_path = POLITICIANS_STAGE_01 / "mgs.pkl"
    mgs_df.to_pickle(save_path)

    # Also save as CSV for easier inspection
    csv_path = POLITICIANS_STAGE_01 / "mgs.csv"
    mgs_df.to_csv(csv_path, index=False)

    print(f"Processed {ui} government members with {entries_count} positions")
    print(f"Saved government members data to: {save_path}")

    return True

if __name__ == "__main__":
    main()
