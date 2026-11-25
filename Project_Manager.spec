# -*- mode: python ; coding: utf-8 -*-
# Build the Windows app with:  pyinstaller Project_Manager.spec
# The result is dist/ProjectMeridian/ProjectMeridian.exe (a folder build: ship the whole folder).

# Images and icons loaded through resource_path()
added_files = [
    ('resources/images/*.png', 'resources/images'),
    ('resources/images/*.jpeg', 'resources/images'),
    ('resources/images/*.ico', 'resources/images'),
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Development tools and unused GUI toolkits don't belong in the app
    # Only PyQt5 is used; other Qt bindings installed alongside it must stay out
    excludes=['tkinter', 'pytest', 'ruff', 'PyQt6', 'PySide2', 'PySide6'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ProjectMeridian',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX-compressed Qt libraries can trip antivirus and occasionally fail to load
    console=False,  # A windowed app: no console window
    icon='resources/images/app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='ProjectMeridian',
)
