# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import customtkinter

ctk_path = os.path.dirname(customtkinter.__file__)

block_cipher = None

added_datas = [
    (ctk_path, 'customtkinter'),
    ('ui/assets', 'ui/assets'),
    ('Imagenes', 'Imagenes'),
]

hidden_imports = [
    'customtkinter',
    'playwright',
    'playwright.sync_api',
    'gspread',
    'google.oauth2',
    'google.oauth2.service_account',
    'google.auth',
    'PIL',
    'PIL._tkinter_finder',
    'faker',
    'threading',
    'csv',
    'json',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GIDEON_4.0',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='Imagenes/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GIDEON_4.0',
)
