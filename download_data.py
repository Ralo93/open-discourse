import requests
import io
import zipfile
import os
from pathlib import Path
import re
import time

# Define standard output directories
DATA_DIR = Path("./data")
RAW_XML_DIR = DATA_DIR / "raw_xml"
RAW_XML_DIR.mkdir(parents=True, exist_ok=True)

# Just the first zip link - the one from the error
zip_link = "https://www.bundestag.de/resource/blob/490392/90738376bb195628b95d117ab5392cfe/pp20-data.zip"

# Extract election period from URL
electoral_term_str = "electoral_term_" + re.search(r"(?<=pp)\d+(?=-data\.zip)", zip_link).group(0)
print(f"Download & unzip '{electoral_term_str}'...")

# Function to download with retries and streaming
def download_large_file(url, max_retries=5):
    for attempt in range(max_retries):
        try:
            print(f"Download attempt {attempt + 1} of {max_retries}...")
            # Use stream=True to avoid loading the entire file into memory
            response = requests.get(url, stream=True, timeout=300)  # Longer timeout (5 minutes)
            response.raise_for_status()  # Raise exception for HTTP errors

            # Get total file size if available
            total_size = int(response.headers.get('content-length', 0))
            print(f"Total file size: {total_size / (1024 * 1024):.2f} MB")

            # Download in chunks to memory
            content = bytearray()
            downloaded = 0
            for chunk in response.iter_content(chunk_size=1024*1024):  # 1MB chunks
                if chunk:
                    content.extend(chunk)
                    downloaded += len(chunk)
                    # Print progress
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"Downloaded: {downloaded / (1024 * 1024):.2f} MB ({percent:.1f}%)", end="\r")

            print("\nDownload completed successfully!")
            return io.BytesIO(content)

        except (requests.exceptions.RequestException, zipfile.BadZipFile) as e:
            print(f"Error during download (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                print("Max retries reached. Download failed.")
                raise

    raise Exception("Download failed after multiple attempts")

try:
    # Download the file
    zip_content = download_large_file(zip_link)

    # Extract the file
    print(f"Extracting files to {RAW_XML_DIR / electoral_term_str}...")
    with zipfile.ZipFile(zip_content) as z:
        save_path = RAW_XML_DIR / electoral_term_str
        save_path.mkdir(parents=True, exist_ok=True)
        z.extractall(save_path)

    print(f"Successfully extracted files to {save_path}")

    # Download MDB Stammdaten (MP base data)
    print("\nDownload & unzip 'MP_BASE_DATA'...")
    mp_base_data_link = "https://www.bundestag.de/resource/blob/472878/7d4d417dbb7f7bd44508b3dc5de08ae2/MdB-Stammdaten-data.zip"
    mp_zip_content = download_large_file(mp_base_data_link)

    with zipfile.ZipFile(mp_zip_content) as z:
        mp_base_data_path = DATA_DIR / "MP_BASE_DATA"
        mp_base_data_path.mkdir(parents=True, exist_ok=True)
        z.extractall(mp_base_data_path)

    print(f"Successfully extracted MP data to {mp_base_data_path}")

except Exception as e:
    print(f"Error: {e}")
    print("\nAlternative download method:")
    print("1. Download the files manually from:")
    print(f"   - {zip_link}")
    print(f"   - {mp_base_data_link}")
    print("2. Create these directories:")
    print(f"   - {RAW_XML_DIR / electoral_term_str}")
    print(f"   - {DATA_DIR / 'MP_BASE_DATA'}")
    print("3. Extract the ZIP files into their respective directories")
