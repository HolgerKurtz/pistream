# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
    ],
    hiddenimports=[
        'cv2',
        'numpy',
        'flask',
        'werkzeug',
        'jinja2',
        'click',
    ],
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
    name='Bird Tracker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
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
    upx=False,
    upx_exclude=[],
    name='Bird Tracker',
)

app = BUNDLE(
    coll,
    name='Bird Tracker.app',
    icon=None,
    bundle_identifier='de.holgerkurtz.birdtracker',
    info_plist={
        'NSCameraUsageDescription': 'Bird Tracker uses the camera to detect birds in the sky.',
        'NSHighResolutionCapable': True,
        'CFBundleDisplayName': 'Bird Tracker',
        'CFBundleShortVersionString': '1.0.0',
    },
)
