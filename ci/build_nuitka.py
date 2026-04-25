"""Nuitka build script for OBS Scene Helper.

Builds the same artifacts as osh.spec (PyInstaller):
  - osh: main GUI app (windowed, no console)
  - osh-display-list: Windows-only console helper for fetching display info

Usage:
    poetry run python ci/build_nuitka.py
"""

import os
import platform
import shutil
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
BUILD_DIR = os.path.join(PROJECT_DIR, "build", "nuitka")
DIST_DIR = os.path.join(PROJECT_DIR, "dist")


def run_nuitka(args):
    cmd = [sys.executable, "-m", "nuitka"] + args
    subprocess.run(cmd, check=True, cwd=PROJECT_DIR)


def build_main_app():
    """Build the main OBS Scene Helper application."""
    system = platform.system()

    args = [
        "--standalone",
        "--enable-plugin=pyside6",
        "--output-filename=osh",
        f"--output-dir={BUILD_DIR}",
    ]

    if system == "Darwin":
        # Use .app bundle on macOS (onefile doesn't support bundles)
        args += [
            "--macos-create-app-bundle",
            "--macos-app-icon=res/app.icns",
            # Hide from dock (LSUIElement)
            "--macos-app-mode=ui-element",
        ]
    else:
        # Use onefile on Windows/Linux
        args.append("--onefile")
        if system == "Windows":
            args += [
                "--windows-console-mode=disable",
                "--windows-icon-from-ico=res/app.ico",
            ]

    args.append("src/obs_scene_helper/__main__.py")

    print("Building main app...")
    run_nuitka(args)

    # Copy final artifact to dist/
    os.makedirs(DIST_DIR, exist_ok=True)
    if system == "Darwin":
        # Nuitka names the bundle after the source file (__main__.app)
        src = os.path.join(BUILD_DIR, "__main__.app")
        dst = os.path.join(DIST_DIR, "osh.app")
        if os.path.exists(dst):
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
    else:
        ext = ".exe" if system == "Windows" else ""
        shutil.copy2(
            os.path.join(BUILD_DIR, f"osh{ext}"),
            os.path.join(DIST_DIR, f"osh{ext}"),
        )


def build_display_list_helper():
    """Build the Windows display list helper (Windows only)."""
    args = [
        "--standalone",
        "--onefile",
        "--enable-plugin=pyside6",
        "--output-filename=osh-display-list",
        f"--output-dir={BUILD_DIR}",
        "--windows-icon-from-ico=res/app.ico",
        "src/obs_scene_helper/controller/system/provider/display_list/windows.py",
    ]

    print("Building display list helper...")
    run_nuitka(args)

    shutil.copy2(
        os.path.join(BUILD_DIR, "osh-display-list.exe"),
        os.path.join(DIST_DIR, "osh-display-list.exe"),
    )


def main():
    build_main_app()

    if platform.system() == "Windows":
        build_display_list_helper()

    print("Build complete. Output in dist/")


if __name__ == "__main__":
    main()
