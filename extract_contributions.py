import pandas as pd
import re
import copy
from pathlib import Path

def convert_to_string(string):
    return "" if string is None else str(string)

def clean_person_name(name_raw):
    """Cleans the person name_raw"""
    # Remove any newlines from the name_raw
    name_raw = re.sub(r"\n", " ", convert_to_string(name_raw))
    # Remove any Additional stuff
    name_raw = re.sub(
        r"(Gegenrufe?\sdes\s|Gegenrufe?\sder\s|Zurufe?\sdes\s|Zurufe?\sder\s)(Abg\s?\.\s)*",
        "",
        name_raw,
    )
    name_raw = re.sub(r"(Abg\s?\.\s?|Abgeordneten\s)", "", name_raw)
    # Remove any Pronouns
    name_raw = re.sub(r"(^\s?der\s?|^\s?die\s?|^\s?das\s?|^\s?von\s?)", "", name_raw)
    # Remove whitespaces at the beginning and at the end
    name_raw = name_raw.lstrip(" ").rstrip(" ")

    # Return the name_raw
    return name_raw

def add_entry(frame, id, type, name_raw, faction, constituency, content, text_position):
    """Adds an entry for every Contribution into the given frame"""
    # Append the corresponding variables to the dictionary
    frame["id"].append(id)
    frame["type"].append(type)
    frame["name_raw"].append(clean_person_name(name_raw))
    frame["faction"].append(convert_to_string(faction))
    frame["constituency"].append(convert_to_string(constituency))
    frame["content"].append(convert_to_string(content))
    frame["text_position"].append(int(text_position))

    # Return the frame
    return frame

def get_government_factions(electoral_term):
    """Get the government factions for the given electoral_term"""
    government_electoral_term = {
        1: ["CDU/CSU", "FDP", "DP"],
        2: ["CDU/CSU", "FDP", "DP"],
        3: ["CDU/CSU", "DP"],
        4: ["CDU/CSU", "FDP"],
        5: ["CDU/CSU", "SPD"],
        6: ["SPD", "FDP"],
        7: ["SPD", "FDP"],
        8: ["SPD", "FDP"],
        9: ["SPD", "FDP"],
        10: ["CDU/CSU", "FDP"],
        11: ["CDU/CSU", "FDP"],
        12: ["CDU/CSU", "FDP"],
        13: ["CDU/CSU", "FDP"],
        14: ["SPD", "BÜNDNIS 90/DIE GRÜNEN"],
        15: ["SPD", "BÜNDNIS 90/DIE GRÜNEN"],
        16: ["CDU/CSU", "SPD"],
        17: ["CDU/CSU", "FDP"],
        18: ["CDU/CSU", "SPD"],
        19: ["CDU/CSU", "SPD"],
        20: ["SPD", "BÜNDNIS 90/DIE GRÜNEN", "FDP"],
    }
    return government_electoral_term.get(electoral_term, [])

def extract_contributions(speech_text, session, identity, text_position=0, text_position_reversed=True):
    """
    Extract contributions (comments, interjections, etc.) from speech text

    Returns:
    - contribution_extended: DataFrame with detailed contribution information
    - cleaned_speech: Speech text with contributions removed
    - contribution_simple: DataFrame with simplified contribution info
    - position_map: Dictionary mapping positions to original text
    """
    # Define patterns for party identification
    parties = {
        "AfD": r"Alternative für Deutschland|AfD",
        "CDU/CSU": r"(?:Gast|-)?(?:\s*C\s*[DSMU]\s*S?[DU]\s*(?:\s*[/,':!.-]?)*\s*(?:\s*C+\s*[DSs]?\s*[UÙ]?\s*)?)(?:-?Hosp\.|-Gast|1)?",
        "SPD": r"\s*'?S(?:PD|DP)(?:\.|-Gast)?",
        "FDP": r"\s*F\.?\s*[PDO][.']?[DP]\.?",
        "BÜNDNIS 90/DIE GRÜNEN": r"(?:BÜNDNIS\s*(?:90)?/?(?:\s*D[1I]E)?|Bündnis\s*90/(?:\s*D[1I]E)?)?\s*[GC]R[UÜ].?\s*[ÑN]EN?(?:/Bündnis 90)?|BÜNDNISSES 90/DIE GRÜNEN|Grünen|BÜNDNISSES 90/ DIE GRÜNEN|BÜNDNIS 90/DIE GRÜNEN",
        "DIE LINKE": r"DIE LIN\s?KEN?|LIN\s?KEN",
        "PDS/Linke Liste": r"(?:Gruppe\s*der\s*)?PDS(?:/(?:LL|Linke Liste))?",
        "fraktionslos": r"(fraktionslos|Parteilos)",
        "GB/BHE": r"(?:GB[/-]\s*)?BHE(?:-DG)?",
        "DP": "DP",
        "KPD": "KPD",
        "Z": r"Z\s|Zentrum",
        "BP": "BP|Bayernpartei",
        "FU": "FU",
        "WAV": "WAV",
        "DRP": r"DRP(\-Hosp\.)?",
        "FVP": "FVP",
        "SSW": "SSW",
        "SRP": "SRP",
        "DA": "DA",
        "Gast": "Gast",
        "DBP": "DBP",
        "NR": "NR",
    }

    # Get electoral term from session
    electoral_term = session // 1000

    # Find all content in brackets - these are likely contributions
    brackets = list(re.finditer(r"\(([^(\)]*(\(([^(\)]*)\))*[^(\)]*)\)", speech_text))

    # Initialize frames for storing contribution data
    frame = {
        "id": [],
        "type": [],
        "name_raw": [],
        "faction": [],
        "constituency": [],
        "content": [],
        "text_position": [],
    }

    contributions_simplified = {
        "text_position": [],
        "content": [],
        "speech_id": []
    }

    # Process brackets in reverse order to avoid position shifting
    for i, bracket in enumerate(reversed(brackets)):
        # Calculate text position
        pos = len(brackets) - 1 - i if text_position_reversed else i + text_position

        # Clean up the text inside bracket
        bracket_text = bracket.group()
        bracket_text_clean = re.sub(r"\n+", " ", bracket_text)
        bracket_text_clean = re.sub(r"\s+", " ", bracket_text_clean)

        # Save the bracket content to simplified contributions
        contributions_simplified["text_position"].append(pos)
        contributions_simplified["content"].append(bracket_text)
        contributions_simplified["speech_id"].append(identity)

        # Replace bracket with marker in the speech text
        deletion_span = bracket.span(1)
        speech_text = (
            speech_text[:deletion_span[0]] +
            "{" + str(pos) + "}" +
            speech_text[deletion_span[1]:]
        )

        # Identify contribution type based on patterns
        if re.search(r"(?i)beifall", bracket_text_clean):
            # Handle applause
            initiator_match = re.search(r"(?i)beifall\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Beifall", "", party_name, "", bracket_text_clean, pos
                        )

                # Check for person names
                person_match = re.search(r"(?:Abg\s?\.\s?)([A-ZÄÖÜa-zäöüß\s]+?)(?:\s*\(|\s*$)", initiator_text)
                if person_match:
                    name_raw = person_match.group(1).strip()
                    frame = add_entry(
                        frame, identity, "Beifall", name_raw, "", "", bracket_text_clean, pos
                    )
            else:
                # General applause without clear attribution
                frame = add_entry(
                    frame, identity, "Beifall", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)zuruf|gegenruf|ruf", bracket_text_clean):
            # Handle interjections/comments
            content_match = re.search(r"(?i)(?:zuruf|gegenruf|ruf)(?:\s*:\s*|\s+von\s+)(.*?)(?:\s*\)|\s*$)", bracket_text_clean)
            initiator_match = re.search(r"(?i)(?:von|des|der)\s+([^:)]+)", bracket_text_clean)

            if content_match:
                content = content_match.group(1).strip()
            else:
                content = ""

            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Zuruf", "", party_name, "", content, pos
                        )

                # Check for person names
                person_match = re.search(r"(?:Abg\s?\.\s?)([A-ZÄÖÜa-zäöüß\s]+?)(?:\s*\(|\s*$)", initiator_text)
                if person_match:
                    name_raw = person_match.group(1).strip()
                    frame = add_entry(
                        frame, identity, "Zuruf", name_raw, "", "", content, pos
                    )
            else:
                # General comment without clear attribution
                frame = add_entry(
                    frame, identity, "Zuruf", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)heiterkeit", bracket_text_clean):
            # Handle cheerfulness/laughter
            initiator_match = re.search(r"(?i)heiterkeit\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Heiterkeit", "", party_name, "", bracket_text_clean, pos
                        )
            else:
                # General cheerfulness without clear attribution
                frame = add_entry(
                    frame, identity, "Heiterkeit", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)widerspruch", bracket_text_clean):
            # Handle objections
            initiator_match = re.search(r"(?i)widerspruch\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Widerspruch", "", party_name, "", bracket_text_clean, pos
                        )
            else:
                # General objection without clear attribution
                frame = add_entry(
                    frame, identity, "Widerspruch", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)unterbrechung", bracket_text_clean):
            # Handle interruptions
            frame = add_entry(
                frame, identity, "Unterbrechung", "", "", "", bracket_text_clean, pos
            )

        elif re.search(r"(?i)unruhe", bracket_text_clean):
            # Handle disturbances
            initiator_match = re.search(r"(?i)unruhe\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Unruhe", "", party_name, "", bracket_text_clean, pos
                        )
            else:
                # General disturbance without clear attribution
                frame = add_entry(
                    frame, identity, "Unruhe", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)lachen", bracket_text_clean):
            # Handle laughter
            initiator_match = re.search(r"(?i)lachen\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Lachen", "", party_name, "", bracket_text_clean, pos
                        )
            else:
                # General laughter without clear attribution
                frame = add_entry(
                    frame, identity, "Lachen", "", "", "", bracket_text_clean, pos
                )

        elif re.search(r"(?i)zustimmung|sehr richtig|sehr wahr|bravo", bracket_text_clean):
            # Handle approval
            initiator_match = re.search(r"(?i)(?:zustimmung|sehr richtig|sehr wahr|bravo)\s+(?:bei|im|der|des|vom)\s+([^)]+)", bracket_text_clean)
            if initiator_match:
                initiator_text = initiator_match.group(1)

                # Check for party mentions
                for party_name, party_pattern in parties.items():
                    if re.search(party_pattern, initiator_text, re.IGNORECASE):
                        frame = add_entry(
                            frame, identity, "Zustimmung", "", party_name, "", bracket_text_clean, pos
                        )
            else:
                # General approval without clear attribution
                frame = add_entry(
                    frame, identity, "Zustimmung", "", "", "", bracket_text_clean, pos
                )
        else:
            # Handle other types of contributions
            frame = add_entry(
                frame, identity, "Sonstiges", "", "", "", bracket_text_clean, pos
            )

    # Convert dictionaries to DataFrames
    contribution_extended = pd.DataFrame(frame)
    contribution_simple = pd.DataFrame(contributions_simplified)

    # Return the results
    return contribution_extended, speech_text, contribution_simple, text_position + len(brackets)

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"

    # Define subdirectories
    CACHE_DIR = DATA_DIR / "cache"
    FINAL_DIR = DATA_DIR / "final"

    SPEECH_CONTENT_DIR = CACHE_DIR / "speech_content"
    SPEECH_CONTENT_STAGE_03 = SPEECH_CONTENT_DIR / "stage_03"
    SPEECH_CONTENT_STAGE_04 = SPEECH_CONTENT_DIR / "stage_04"

    CONTRIBUTIONS_EXTENDED_DIR = CACHE_DIR / "contributions_extended"
    CONTRIBUTIONS_EXTENDED_STAGE_01 = CONTRIBUTIONS_EXTENDED_DIR / "stage_01"

    # Create directories if they don't exist
    for directory in [
        DATA_DIR, CACHE_DIR, FINAL_DIR,
        SPEECH_CONTENT_DIR, SPEECH_CONTENT_STAGE_03, SPEECH_CONTENT_STAGE_04,
        CONTRIBUTIONS_EXTENDED_DIR, CONTRIBUTIONS_EXTENDED_STAGE_01,
    ]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Extracting contributions from speeches...")

    speech_id = 0
    simplified_list = []
    processed_terms = 0

    # Process each electoral term folder
    for folder_path in sorted(SPEECH_CONTENT_STAGE_03.glob("electoral_term_*")):
        if not folder_path.is_dir():
            continue

        # Extract the term number
        term_number = re.search(r"(?<=electoral_term_)\d{2}", folder_path.stem)
        if term_number is None:
            continue
        term_number = int(term_number.group(0))

        print(f"Processing electoral term {term_number}...")

        # Create output directories
        speech_output_dir = SPEECH_CONTENT_STAGE_04 / folder_path.stem
        extended_output_dir = CONTRIBUTIONS_EXTENDED_STAGE_01 / folder_path.stem

        speech_output_dir.mkdir(parents=True, exist_ok=True)
        extended_output_dir.mkdir(parents=True, exist_ok=True)

        # Process each speech file
        file_count = len(list(folder_path.glob("*.pkl")))
        processed_count = 0

        for speech_file in folder_path.glob("*.pkl"):
            try:
                # Read the speech content
                speech_content = pd.read_pickle(speech_file)

                # Add speech_id column
                speech_content.insert(0, "speech_id", 0)

                # Process each speech in the file
                extended_list = []

                for counter, speech in enumerate(speech_content["speech_content"]):
                    # Extract contributions from the speech
                    contribution_extended, cleaned_speech, contribution_simple, _ = extract_contributions(
                        speech,
                        int(speech_file.stem),
                        speech_id
                    )

                    # Add to lists for saving
                    simplified_list.append(contribution_simple)
                    extended_list.append(contribution_extended)

                    # Update speech content with cleaned speech
                    speech_content.at[counter, "speech_content"] = cleaned_speech
                    speech_content.at[counter, "speech_id"] = speech_id

                    # Increment speech ID for next speech
                    speech_id += 1

                # Combine all contributions for this file
                if extended_list:
                    contributions_extended = pd.concat(extended_list, sort=False)

                    # Save contributions and updated speech content
                    contributions_extended.to_pickle(extended_output_dir / speech_file.name)
                    speech_content.to_pickle(speech_output_dir / speech_file.name)

                processed_count += 1
                if processed_count % 10 == 0 or processed_count == file_count:
                    print(f"  Processed {processed_count}/{file_count} files")

            except Exception as e:
                print(f"  Error processing {speech_file.name}: {e}")

        processed_terms += 1
        print(f"  Extracted contributions from {processed_count} speeches")

    # Combine all simplified contributions and save
    print("Creating simplified contributions file...")
    if simplified_list:
        contributions_simplified = pd.concat(simplified_list, sort=False)

        # Save to final directory
        contributions_simplified.to_pickle(FINAL_DIR / "contributions_simplified.pkl")
        print(f"Saved simplified contributions to {FINAL_DIR / 'contributions_simplified.pkl'}")

    print(f"Extracted contributions from speeches in {processed_terms} electoral terms")
    return True

if __name__ == "__main__":
    main()
