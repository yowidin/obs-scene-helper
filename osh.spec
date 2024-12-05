block_cipher = None


main_app_analysis = Analysis(
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

win_display_getter_analysis = Analysis(
    ['src/obs_scene_helper/controller/system/provider/display_list/windows.py'],
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

main_pyz = PYZ(main_app_analysis.pure, main_app_analysis.zipped_data, cipher=block_cipher)

win_display_list_pyz = PYZ(win_display_getter_analysis.pure, win_display_getter_analysis.zipped_data, cipher=block_cipher)

exe_main = EXE(
    main_pyz,
    main_app_analysis.scripts,
    main_app_analysis.binaries,
    main_app_analysis.zipfiles,
    main_app_analysis.datas,
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

exe_display_list = EXE(
    win_display_list_pyz,
    win_display_getter_analysis.scripts,
    win_display_getter_analysis.binaries,
    win_display_getter_analysis.zipfiles,
    win_display_getter_analysis.datas,
    [],
    name='osh-display-list',
    icon="res/app.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

app = BUNDLE(
    exe_main,
    name='osh.app',
    icon="res/app.icns",
    bundle_identifier=None,

    # Don't appear in the dock
    # https://pyinstaller.org/en/stable/spec-files.html#spec-file-options-for-a-macos-bundle
    # https://wiki.lazarus.freepascal.org/Hiding_a_macOS_app_from_the_Dock
    # https://stackoverflow.com/questions/59601635/hide-a-running-app-from-mac-dock-without-effecting-apps-ui-not-using-lsuieleme
    info_plist={'LSUIElement': True}
)