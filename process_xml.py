import xml.etree.ElementTree as et
import re
from pathlib import Path
import dicttoxml
import sys

# Set default encoding to utf-8 for all file operations
sys.stdout.reconfigure(encoding='utf-8')

# Define standard directories
DATA_DIR = Path("./data")
RAW_XML_DIR = DATA_DIR / "raw_xml"
RAW_TXT_DIR = DATA_DIR / "raw_txt"
RAW_TXT_DIR.mkdir(parents=True, exist_ok=True)

# Get the election term directory (only processing the first one)
term_folders = list(RAW_XML_DIR.glob("electoral_term_*"))
if not term_folders:
    print("No electoral term folders found. Make sure to run download_data.py first.")
    exit(1)

term_folder = term_folders[0]
term_number = int(re.search(r"(?<=electoral_term_)\d{2}", term_folder.stem).group(0))

print(f"Parsing term {term_number}...")

# Common regex patterns for session begin and end
begin_pattern = re.compile(r"Beginn?:?\s?(\d){1,2}(\s?[.,]\s?(\d){1,2})?\s?Uhr")
end_pattern = re.compile(r"\(Schlu(ß|ss)\s?:?(.*?)\d{1,2}\D+(\d{1,2})?(.*?)\)?|\(Ende der Sitzung: \d{1,2}\D+(\d{1,2}) Uhr\.?\)")

# Function to replace problem characters
def clean_text(text):
    if text is None:
        return ""

    # Replace problematic characters with similar ASCII characters or descriptive replacements
    replacements = {
        '\u011f': 'g',  # ğ -> g
        '\uf020': ' ',  # private use character -> space
        # Add more replacements as needed
    }

    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text

# Process each XML file in the directory
for xml_file_path in term_folder.glob("*.xml"):
    try:
        print(f"Processing {xml_file_path.name}")
        tree = et.parse(xml_file_path)

        # Extract metadata
        meta_data = {
            "document_number": tree.find("NR").text,
            "date": tree.find("DATUM").text
        }

        # Get text content and clean it
        text_corpus = tree.find("TEXT").text
        if text_corpus is None:
            print(f"  Skipping - no text content found")
            continue

        # Clean problematic characters before further processing
        text_corpus = clean_text(text_corpus)
        text_corpus = text_corpus.replace("\r", "")

        # Find beginning of session
        find_beginnings = list(re.finditer(begin_pattern, text_corpus))
        if len(find_beginnings) != 1:
            print(f"  Skipping - couldn't identify unique session beginning (found {len(find_beginnings)})")
            continue

        beginning_of_session = find_beginnings[0].span()[1]

        # Split into TOC and session content
        toc = text_corpus[:beginning_of_session]
        session_content = text_corpus[beginning_of_session:]

        # Add end marker to help with regex
        session_content += "\n\nEND OF FILE"

        # Find end of session
        find_endings = list(re.finditer(end_pattern, session_content))
        if len(find_endings) != 1:
            print(f"  Skipping - couldn't identify unique session ending (found {len(find_endings)})")
            continue

        end_of_session = find_endings[0].span()[0]

        # Split content and appendix
        appendix = session_content[end_of_session:]
        session_content = session_content[:end_of_session]

        # Save the processed files
        save_path = RAW_TXT_DIR / term_folder.stem / xml_file_path.stem
        save_path.mkdir(parents=True, exist_ok=True)

        # Use utf-8 encoding explicitly when writing files
        with open(save_path / "toc.txt", "w", encoding="utf-8") as text_file:
            text_file.write(toc)

        with open(save_path / "session_content.txt", "w", encoding="utf-8") as text_file:
            text_file.write(session_content)

        with open(save_path / "appendix.txt", "w", encoding="utf-8") as text_file:
            text_file.write(appendix)

        # For the XML file, we use bytes mode which doesn't have encoding issues
        with open(save_path / "meta_data.xml", "wb") as result_file:
            result_file.write(dicttoxml.dicttoxml(meta_data))

        print(f"  Success - saved to {save_path}")

    except Exception as e:
        print(f"  Error processing {xml_file_path.name}: {e}")
        # Uncomment for debugging
        # import traceback
        # traceback.print_exc()
