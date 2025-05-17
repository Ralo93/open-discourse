import pandas as pd
import re
from pathlib import Path
import os

def main():
    # Use a simpler, relative path structure
    ROOT_DIR = Path.cwd()  # Current working directory
    DATA_DIR = ROOT_DIR / "data"
    RAW_TXT_DIR = DATA_DIR / "raw_txt"  # Directory containing the raw text files from XML
    CACHE_DIR = DATA_DIR / "cache"
    SPEECH_CONTENT_DIR = CACHE_DIR / "speech_content"
    SPEECH_CONTENT_STAGE_01 = SPEECH_CONTENT_DIR / "stage_01"

    # Create directories if they don't exist
    for directory in [DATA_DIR, CACHE_DIR, SPEECH_CONTENT_DIR, SPEECH_CONTENT_STAGE_01]:
        directory.mkdir(parents=True, exist_ok=True)

    print("Extracting speeches from raw text files...")

    # Define standard name-with-parentheses pattern
    standard_pattern = re.compile(
        r'(?:^|\n)\s*([A-Za-zäöüÄÖÜß\.\-\s]+)\s*\(([^)]+)\):',
        re.MULTILINE
    )

    # Define position pattern
    position_pattern = re.compile(
        r'(?:^|\n)\s*([A-Za-zäöüÄÖÜß\.\-\s]+),\s+([^:]+):',
        re.MULTILINE
    )

    # Define bundestag format pattern with explicit name repetition
    # Format: "AlexanderHoffmannCDU/CSUAlexander Hoffmann (CDU/CSU):"
    bundestag_pattern = re.compile(
        r'(?:^|\n)\s*([A-Za-zäöüÄÖÜß\.]+)([^:]+)\(([^)]+)\):',
        re.MULTILINE
    )

    # Find all session directories in raw_txt
    session_dirs = [d for d in RAW_TXT_DIR.glob("*") if d.is_dir()]

    if not session_dirs:
        print(f"Error: No session directories found in {RAW_TXT_DIR}")
        return False

    print(f"Found {len(session_dirs)} session directories.")

    # Process each session directory
    processed_count = 0

    for session_dir in session_dirs:
        session_name = session_dir.name
        print(f"Processing session {session_name}...")

        # Read the session content file
        session_content_file = session_dir / "session_content.txt"

        if not session_content_file.exists():
            print(f"  ⚠️  Missing session content file in {session_name}")
            continue

        try:
            with open(session_content_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ Error reading file {session_content_file}: {e}")
            continue

        # Find all matches for each pattern
        speakers = []

        # Track which patterns find what (for debugging)
        pattern_counts = {"bundestag": 0, "standard": 0, "position": 0}

        # Track matches for specific parties
        party_matches = {
            "CDU/CSU": 0,
            "BÜNDNIS 90/DIE GRÜNEN": 0,
            "SPD": 0,
            "AfD": 0,
            "DIE LINKE": 0
        }

        # 1. First try the bundestag specific pattern
        for match in bundestag_pattern.finditer(content):
            name_part = match.group(2).strip()
            party = match.group(3).strip()

            # Look for a clean name in the middle section
            name_match = re.search(r'([A-Za-zäöüÄÖÜß\.\s]+)$', name_part)
            if name_match:
                name_raw = name_match.group(1).strip()
            else:
                name_raw = name_part

            # Update party counts
            for p in party_matches:
                if p in party:
                    party_matches[p] += 1

            speakers.append({
                'name_raw': name_raw,
                'position_raw': party,
                'span_begin': match.start(),
                'span_end': match.end(),
                'pattern_type': 'bundestag'
            })
            pattern_counts["bundestag"] += 1

        # 2. Standard pattern (Name (Party):)
        for match in standard_pattern.finditer(content):
            name = match.group(1).strip()
            party = match.group(2).strip()

            # Update party counts
            for p in party_matches:
                if p in party:
                    party_matches[p] += 1

            speakers.append({
                'name_raw': name,
                'position_raw': party,
                'span_begin': match.start(),
                'span_end': match.end(),
                'pattern_type': 'standard'
            })
            pattern_counts["standard"] += 1

        # 3. Position pattern
        for match in position_pattern.finditer(content):
            speakers.append({
                'name_raw': match.group(1).strip(),
                'position_raw': match.group(2).strip(),
                'span_begin': match.start(),
                'span_end': match.end(),
                'pattern_type': 'position'
            })
            pattern_counts["position"] += 1

        # Sort speakers by position in text
        speakers.sort(key=lambda x: x['span_begin'])

        # Remove overlapping matches
        non_overlapping_speakers = []
        for speaker in speakers:
            # Check if this speaker overlaps with any already included speaker
            overlapping = False
            for existing in non_overlapping_speakers:
                if (speaker['span_begin'] <= existing['span_end'] and
                    speaker['span_end'] >= existing['span_begin']):
                    overlapping = True
                    break
            if not overlapping:
                non_overlapping_speakers.append(speaker)

        speakers = non_overlapping_speakers

        if not speakers:
            print(f"  ⚠️  No speakers found in {session_name}")
            continue

        print(f"  + Pattern matches: {pattern_counts}")
        print(f"  + Party matches: {party_matches}")

        # Create DataFrame
        df = pd.DataFrame(speakers)

        # Get session date if available
        session_date = ""
        meta_file = session_dir / "meta_data.xml"
        if meta_file.exists():
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(meta_file)
                date_elem = tree.find(".//date")
                if date_elem is not None and date_elem.text:
                    session_date = date_elem.text
            except Exception as e:
                print(f"  Warning: Could not parse metadata for {session_name}: {e}")

        # Add session information
        df['session'] = session_name
        df['session_date'] = session_date

        # Extract speech content - this is where one speaker's text ends and the next begins
        speech_beginnings = df["span_end"].tolist()
        speech_endings = df["span_begin"].tolist()[1:] + [len(content)]

        df["speech_content"] = [content[begin:end].strip() for begin, end in zip(speech_beginnings, speech_endings)]

        # Filter out extremely short speeches (likely noise)
        df = df[df['speech_content'].str.len() > 30]

        # Filter out speeches that are purely annotations
        df = df[~df['speech_content'].str.match(r'^\([^)]+\)$')]

        # Process for "constituency" to be compatible with original code
        df['constituency'] = ""

        # Count the occurrences of each party in the final DataFrame
        party_counts = {}
        for party in party_matches:
            party_counts[party] = df['position_raw'].str.contains(party, regex=False).sum()

        print(f"  + Final party counts in position_raw: {party_counts}")

        # Save to pickle file
        output_path = SPEECH_CONTENT_STAGE_01 / f"{session_name}.pkl"
        df.to_pickle(output_path)
        print(f"  + Saved {len(df)} speeches from session {session_name}")
        processed_count += 1

    print(f"\nSpeech extraction complete: {processed_count} sessions processed.")
    return True

if __name__ == "__main__":
    main()
