import os
import subprocess

print("Starting Bundestag data processing pipeline...")

# Run each script in sequence
scripts = [
   # "download_data.py",
   # "process_xml.py",
    "process_mp_data.py"
]

for script in scripts:
    print(f"\nRunning {script}...")
    result = subprocess.run(["python", script], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(f"Errors:\n{result.stderr}")

print("\nProcessing pipeline complete!")
