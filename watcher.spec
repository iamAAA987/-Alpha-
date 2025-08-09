# -*- mode: python ; coding: utf-8 -*-

import os
import pathlib
import sys

playwright_datas = []
# Collect all playwright browser data
try:
    # Determine the default playwright browser path based on OS
    if sys.platform == "win32":
        playwright_browsers_path = pathlib.Path.home() / "AppData/Local/ms-playwright"
    elif sys.platform == "darwin":
        playwright_browsers_path = pathlib.Path.home() / "Library/Caches/ms-playwright"
    else:
        playwright_browsers_path = pathlib.Path.home() / ".cache/ms-playwright"

    if playwright_browsers_path.exists():
        for browser_dir in playwright_browsers_path.iterdir():
            if browser_dir.is_dir():
                playwright_datas.append((
                    str(browser_dir),
                    os.path.join('playwright', 'driver', 'package', '.local-browsers', browser_dir.name)
                ))
    else:
        print(f"Warning: Playwright browser path not found at {playwright_browsers_path}")
        print("Please run 'playwright install' to install browsers.")

except Exception as e:
    print(f"Warning: Failed to package playwright browsers: {e}")

# ---------------- watcher backend ----------------

a = Analysis(
    ['watcher.py'],
    pathex=[],
    binaries=[],
    datas=[('config.ini', '.')] + playwright_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='watcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# ---------------- GUI frontend ----------------

a_gui = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[('config.ini', '.')] + playwright_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz_gui = PYZ(a_gui.pure)

exe_gui = EXE(
    pyz_gui,
    a_gui.scripts,
    a_gui.binaries,
    a_gui.datas,
    [],
    name='watcher-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
