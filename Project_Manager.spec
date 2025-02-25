# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Add your resource files here
added_files = [
    ('resources/images/*.png', 'resources/images'),
    ('resources/images/*.jpeg', 'resources/images'),
    # Add any other resource files here
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_files,  # Include your resource files
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YourAppName',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # This is the same as --windowed
    icon='path\\to\\icon.ico',  # Optional: add your icon path
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YourAppName',
)