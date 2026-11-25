@echo off
rem Build the Windows app into dist\ProjectMeridian\ (ship that whole folder).
rem Install the build tools once with: pip install -r requirements-dev.txt
pyinstaller --noconfirm Project_Manager.spec
