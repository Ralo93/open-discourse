#import od_lib.definitions.path_definitions as path_definitions
import requests
import io
import zipfile
import regex

# output directory
RAW_XML = path_definitions.RAW_XML

zip_links = [
    "https://www.bundestag.de/resource/blob/490392/90738376bb195628b95d117ab5392cfe/pp20-data.zip",

]


for link in zip_links:
    # Extract election period from URL
    electoral_term_str = "electoral_term_" + regex.search(
            r"(?<=pp)\d+(?=-data\.zip)", link
        ).group(0)
    print(f"Download & unzip '{electoral_term_str}'...", end="", flush=True)
    r = requests.get(link)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        save_path = RAW_XML / electoral_term_str
        save_path.mkdir(parents=True, exist_ok=True)
        z.extractall(save_path)
    print("Done.")


# Download MDB Stammdaten.
mp_base_data_link = "https://www.bundestag.de/resource/blob/472878/7d4d417dbb7f7bd44508b3dc5de08ae2/MdB-Stammdaten-data.zip"  # noqa: E501

print("Download & unzip 'MP_BASE_DATA'...", end="", flush=True)
r = requests.get(mp_base_data_link)
with zipfile.ZipFile(io.BytesIO(r.content)) as z:
    mp_base_data_path = path_definitions.DATA_RAW / "MP_BASE_DATA"
    mp_base_data_path.mkdir(parents=True, exist_ok=True)
    z.extractall(mp_base_data_path)
print("Done.")

