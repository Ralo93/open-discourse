import requests
import io
import zipfile
import os
from pathlib import Path
import re

# Define standard output directories
DATA_DIR = Path("./data")
RAW_XML_DIR = DATA_DIR / "raw_xml"
RAW_XML_DIR.mkdir(parents=True, exist_ok=True)

# Just the first zip link
zip_link = "https://www.bundestag.de/resource/blob/490392/90738376bb195628b95d117ab5392cfe/pp20-data.zip"

# Extract election period from URL
electoral_term_str = "electoral_term_" + re.search(r"(?<=pp)\d+(?=-data\.zip)", zip_link).group(0)
print(f"Download & unzip '{electoral_term_str}'...", end="", flush=True)

# Download and extract
r = requests.get(zip_link)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    save_path = RAW_XML_DIR / electoral_term_str
    save_path.mkdir(parents=True, exist_ok=True)
    z.extractall(save_path)
print("Done.")

# Download MDB Stammdaten (MP base data)
mp_base_data_link = "https://www.bundestag.de/resource/blob/472878/7d4d417dbb7f7bd44508b3dc5de08ae2/MdB-Stammdaten-data.zip"
print("Download & unzip 'MP_BASE_DATA'...", end="", flush=True)
r = requests.get(mp_base_data_link)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    mp_base_data_path = DATA_DIR / "MP_BASE_DATA"
    mp_base_data_path.mkdir(parents=True, exist_ok=True)
    z.extractall(mp_base_data_path)
print("Done.")
