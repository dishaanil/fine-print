#!/bin/bash

# This script runs every time your Studio starts, from your home directory.

# Logs from previous runs can be found in ~/.lightning_studio/logs/

# List files under fast_load that need to load quickly on start (e.g. model checkpoints).
#
# ! fast_load
# <your file here>

# Add your startup commands below.
#
# Example: streamlit run my_app.py
# Example: gradio my_app.py
python - <<'EOF'
import os

import toml

file_path = os.path.expanduser("~/.streamlit/config.toml")
theme = os.environ.get("LIGHTNING_THEME", None)

if theme not in ["light", "dark"]:
    print("No valid LIGHTNING_THEME set. Exiting.")
    exit(0)

# Read existing content or create empty object
try:
    with open(file_path, "r") as f:
        data = toml.load(f)
except (toml.TomlDecodeError, FileNotFoundError):
    data = {}

data.setdefault("theme", {})

# Get current value
current_value = data.get("theme", {}).get("base", None)

# Only update if the current value is 'light', 'dark', or doesn't exist
if current_value in ["light", "dark", None]:
    data["theme"]["base"] = theme
    data["theme"]["primaryColor"] = "6019C8"
    print(f"Updated streamlit theme to {theme}")
else:
    print(f"Skipping update - current value '{current_value}' is not 'light' or 'dark'")

with open(file_path, "w") as f:
    toml.dump(data, f)

EOF
streamlit run --server.port 8000 main.py
