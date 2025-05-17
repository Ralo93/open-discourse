import streamlit as st
import pandas as pd
import os
from pathlib import Path

st.set_page_config(layout="wide")
st.title("📦 File Inspector")

# Get list of files in current directory and all subdirectories
base_dir = Path(".")
pkl_files = list(base_dir.rglob("*.pkl"))
csv_files = list(base_dir.rglob("*.csv"))
txt_files = list(base_dir.rglob("*.txt"))
xml_files = list(base_dir.rglob("*.xml"))

# Section for .pkl files
st.header("🔍 Inspect Pickle Files")
if not pkl_files:
    st.warning("No .pkl files found.")
else:
    pkl_path = st.selectbox("Select a .pkl file to inspect:", [str(f) for f in pkl_files])

    if pkl_path:
        try:
            obj = pd.read_pickle(pkl_path)
            if isinstance(obj, pd.DataFrame):
                st.success(f"Loaded DataFrame with shape {obj.shape}")
                st.dataframe(obj)
                with st.expander("Show column info and filter"):
                    st.write("Columns:", obj.columns.tolist())
                    columns_to_show = st.multiselect("Select columns to show:", options=obj.columns.tolist(), default=obj.columns.tolist())
                    st.dataframe(obj[columns_to_show])
            else:
                st.error(f"This file does not contain a pandas DataFrame. It's a {type(obj)}")
        except Exception as e:
            st.exception(f"Error loading file: {e}")

# Section for .csv files
st.header("🔍 Inspect CSV Files")
if not csv_files:
    st.warning("No .csv files found.")
else:
    csv_path = st.selectbox("Select a .csv file to inspect:", [str(f) for f in csv_files])

    if csv_path:
        try:
            df_csv = pd.read_csv(csv_path)
            st.success(f"Loaded CSV with shape {df_csv.shape}")
            st.dataframe(df_csv)
            with st.expander("Show column info and filter"):
                st.write("Columns:", df_csv.columns.tolist())
                columns_to_show_csv = st.multiselect("Select columns to show:", options=df_csv.columns.tolist(), default=df_csv.columns.tolist(), key="csv")
                st.dataframe(df_csv[columns_to_show_csv])
        except Exception as e:
            st.exception(f"Error loading file: {e}")

# Section for .txt files
st.header("📝 Inspect TXT Files")
if not txt_files:
    st.warning("No .txt files found.")
else:
    txt_path = st.selectbox("Select a .txt file to inspect:", [str(f) for f in txt_files])

    if txt_path:
        try:
            with open(txt_path, "r", encoding="utf-8") as file:
                txt_content = file.read()
            st.text_area("Contents of the TXT file:", txt_content, height=300)
        except Exception as e:
            st.exception(f"Error loading file: {e}")

# Section for .xml files
st.header("🧾 Inspect XML Files")
if not xml_files:
    st.warning("No .xml files found.")
else:
    xml_path = st.selectbox("Select a .xml file to inspect:", [str(f) for f in xml_files])

    if xml_path:
        try:
            with open(xml_path, "r", encoding="utf-8") as file:
                xml_content = file.read()
            st.text_area("Contents of the XML file:", xml_content, height=300)
        except Exception as e:
            st.exception(f"Error loading file: {e}")
