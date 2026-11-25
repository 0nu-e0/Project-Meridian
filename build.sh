#!/bin/sh
# Build the macOS app into dist/ProjectMeridian.app (drag it into Applications).
# Install the build tools once with: pip install -r requirements-dev.txt
# For the Windows .exe, run build.bat on Windows: PyInstaller builds for the system it runs on.
cd "$(dirname "$0")" || exit 1
python -m PyInstaller --noconfirm Project_Manager.spec
