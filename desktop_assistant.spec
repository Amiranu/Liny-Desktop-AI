# -*- mode: python ; coding: utf-8 -*-
"""
Production PyInstaller specification for Liny Desktop AI Assistant.
Packages all Qt GUI, audio, vision, and system control dependencies into a standalone executable.
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs

block_cipher = None

# Collect package data and dynamic libraries
datas = [
    ("config.yaml", "."),
    ("assets", "assets"),
]

binaries = []
hiddenimports = [
    # Qt
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
    # Audio
    "sounddevice",
    "numpy",
    "pvporcupine",
    "edge_tts",
    "aiohttp",
    # Vision & Hands
    "mss",
    "PIL",
    "PIL.Image",
    "pyautogui",
    "pyperclip",
    # Hotkeys
    "pynput",
    "pynput.keyboard",
    "pynput.keyboard._win32",
    "pynput.mouse",
    "pynput.mouse._win32",
    # System
    "ctypes",
    "ctypes.wintypes",
    "webbrowser",
]

# Collect sounddevice binaries (PortAudio DLL)
try:
    sd_datas, sd_binaries, sd_hidden = collect_all("sounddevice")
    datas += sd_datas
    binaries += sd_binaries
    hiddenimports += sd_hidden
except Exception:
    pass

# Collect pvporcupine data files if present
try:
    pvc_datas, pvc_binaries, pvc_hidden = collect_all("pvporcupine")
    datas += pvc_datas
    binaries += pvc_binaries
    hiddenimports += pvc_hidden
except Exception:
    pass

# Collect edge-tts data files
try:
    et_datas, et_binaries, et_hidden = collect_all("edge_tts")
    datas += et_datas
    hiddenimports += et_hidden
except Exception:
    pass

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "scipy"],
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
    name="LinyDesktopAI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Windowed GUI mode: no background CMD prompt
    icon="assets/app_icon.ico",
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="LinyDesktopAI",
)

