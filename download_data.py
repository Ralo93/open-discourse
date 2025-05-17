import requests
import io
import zipfile
import os
from pathlib import Path
import re

# Define output directories
DATA_DIR = Path("./data")
RAW_XML_DIR = DATA_DIR / "raw_xml"
RAW_XML_DIR.mkdir(parents=True, exist_ok=True)

# Bundestag XML files (plain XML, not ZIPs!)
xml_links = [
    "https://www.bundestag.de/resource/blob/1067368/ae8fee796e9ffd478a18e411a88816f2/21003.xml",
    "https://www.bundestag.de/resource/blob/1067464/8532b8fc98ef08b752cce31ef8505a10/21004.xml",
    "https://www.bundestag.de/resource/blob/1058872/eae99eeaf539454011d98918f336ada7/21001.xml",
    "https://www.bundestag.de/resource/blob/1064580/5c36bdcfce269e58d5f23f4bece5d44c/21002.xml"
]

# Download XMLs
for link in xml_links:
    filename = link.split("/")[-1]  # Extract e.g. 21003.xml
    save_path = RAW_XML_DIR / filename
    print(f"Downloading {filename}...", end="", flush=True)
    r = requests.get(link)
    with open(save_path, "wb") as f:
        f.write(r.content)
    print("Done.")

# Download MDB Stammdaten (MP base data ZIP file)
mp_base_data_link = "https://www.bundestag.de/resource/blob/472878/7d4d417dbb7f7bd44508b3dc5de08ae2/MdB-Stammdaten-data.zip"
print("Download & unzip 'MP_BASE_DATA'...", end="", flush=True)
r = requests.get(mp_base_data_link)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    mp_base_data_path = DATA_DIR / "MP_BASE_DATA"
    mp_base_data_path.mkdir(parents=True, exist_ok=True)
    z.extractall(mp_base_data_path)
print("Done.")
