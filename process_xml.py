import xml.etree.ElementTree as et
import re
from pathlib import Path
import dicttoxml
import sys

# Set default encoding
sys.stdout.reconfigure(encoding="utf-8")

# Define directories
DATA_DIR = Path("./data")
RAW_XML_DIR = DATA_DIR / "raw_xml"
RAW_TXT_DIR = DATA_DIR / "raw_txt"
RAW_TXT_DIR.mkdir(parents=True, exist_ok=True)

def clean_text(text):
    """Clean text by handling various character encodings."""
    if text is None:
        return ""
    # Handle various special characters and encodings
    replacements = {
        '\u011f': 'g',
        '\uf020': ' ',
        'Ã¤': 'ä',
        'Ã¼': 'ü',
        'Ã¶': 'ö',
        'Ã„': 'Ä',
        'Ãœ': 'Ü',
        'Ã–': 'Ö',
        'ÃŸ': 'ß'
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def extract_text_from_element(element):
    """Recursively extract all text content from an element and its children."""
    if element is None:
        return ""

    text = element.text or ""
    for child in element:
        text += extract_text_from_element(child)
        if child.tail:
            text += child.tail

    return text

def process_xml_file(xml_file_path):
    """Process a single XML file and extract its contents."""
    print(f"Processing {xml_file_path.name}")

    try:
        # Parse the XML file
        tree = et.parse(xml_file_path)
        root = tree.getroot()

        # Extract metadata
        meta_data = {
            "document_number": "",
            "date": ""
        }

        # Extract document number and date from plenarprotokoll-nummer or wahlperiode/sitzungsnr
        plenarprotokoll_nummer = root.find(".//plenarprotokoll-nummer")
        if plenarprotokoll_nummer is not None:
            meta_data["document_number"] = extract_text_from_element(plenarprotokoll_nummer).strip()

        # Try to get wahlperiode and sitzungsnr
        wahlperiode = root.find(".//wahlperiode")
        sitzungsnr = root.find(".//sitzungsnr")
        if wahlperiode is not None and sitzungsnr is not None:
            if not meta_data["document_number"]:
                meta_data["document_number"] = f"{wahlperiode.text}/{sitzungsnr.text}"

        # Get the date
        datum = root.find(".//datum")
        if datum is not None:
            meta_data["date"] = datum.text if datum.text else (datum.get("date") or "")

        # Initialize sections with empty strings
        toc = ""
        session_content = ""
        appendix = ""

        # Extract table of contents (vorspann section)
        vorspann = root.find(".//vorspann")
        if vorspann is not None:
            toc = extract_text_from_element(vorspann).strip()

        # Extract session content (sitzungsverlauf section)
        sitzungsverlauf = root.find(".//sitzungsverlauf")
        if sitzungsverlauf is not None:
            session_content = extract_text_from_element(sitzungsverlauf).strip()

        # Extract appendix (anlagen section)
        anlagen = root.find(".//anlagen")
        if anlagen is not None:
            appendix = extract_text_from_element(anlagen).strip()

        # If there's no clear structure, try to extract content from rede elements
        if not session_content:
            speeches = []
            for rede in root.findall(".//rede"):
                speech_text = extract_text_from_element(rede).strip()
                if speech_text:
                    speeches.append(speech_text)

            if speeches:
                session_content = "\n\n".join(speeches)

        # If still no content, use the entire document as session content
        if not session_content:
            session_content = extract_text_from_element(root).strip()
            if toc:
                session_content = session_content.replace(toc, "", 1).strip()
            if appendix:
                session_content = session_content.replace(appendix, "", 1).strip()

        # Clean the text
        toc = clean_text(toc.replace("\r", ""))
        session_content = clean_text(session_content.replace("\r", ""))
        appendix = clean_text(appendix.replace("\r", ""))

        # Save results
        save_path = RAW_TXT_DIR / xml_file_path.stem
        save_path.mkdir(parents=True, exist_ok=True)

        (save_path / "toc.txt").write_text(toc, encoding="utf-8")
        (save_path / "session_content.txt").write_text(session_content, encoding="utf-8")
        (save_path / "appendix.txt").write_text(appendix, encoding="utf-8")
        (save_path / "meta_data.xml").write_bytes(dicttoxml.dicttoxml(meta_data))

        print(f"  ✅ Saved parsed output to {save_path}")
        return True

    except Exception as e:
        print(f"  ❌ Error processing {xml_file_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return False

# Process each XML file
successful = 0
failed = 0
for xml_file_path in RAW_XML_DIR.glob("*.xml"):
    if process_xml_file(xml_file_path):
        successful += 1
    else:
        failed += 1

print(f"\nProcessing complete. Successfully processed {successful} files, {failed} failed.")
