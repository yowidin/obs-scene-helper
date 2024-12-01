block_cipher = None


a = Analysis(
    ['src/obs_scene_helper/__main__.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='osh',
    icon="res/app.ico",
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
app = BUNDLE(
    exe,
    name='osh.app',
    icon="res/app.icns",
    bundle_identifier=None,

    # Don't appear in the dock
    # https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle
    # https://wiki.lazarus.freepascal.org/Hiding_a_macOS_app_from_the_Dock
    # https://stackoverflow.com/questions/59601635/hide-a-running-app-from-mac-dock-without-effecting-apps-ui-not-using-lsuieleme
    info_plist={'LSUIElement': True}
)