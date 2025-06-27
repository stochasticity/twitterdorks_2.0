#!/bin/bash
# This script runs after Streamlit Cloud installs Python dependencies
# It ensures Playwright downloads its browser binaries

echo "▶ Running post-install.sh: installing Playwright browsers..."
playwright install chromium

