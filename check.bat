@echo off
rem Lint and test everything. Install the tools once with: pip install -r requirements-dev.txt
ruff check . || exit /b 1
python -m pytest %*
