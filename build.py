"""
One-click standalone packaging script for Liny Desktop AI.
Cleans build artifacts, bundles the application via PyInstaller,
stages distribution files, and verifies executable integrity.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"
SPEC_FILE = ROOT_DIR / "desktop_assistant.spec"
OUTPUT_DIR = DIST_DIR / "LinyDesktopAI"
EXE_FILE = OUTPUT_DIR / ("LinyDesktopAI.exe" if sys.platform == "win32" else "LinyDesktopAI")


def run_command(cmd: list[str]) -> bool:
    print(f"\n>> Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT_DIR))
    return result.returncode == 0


def clean_artifacts() -> None:
    print(">> Cleaning previous build artifacts...")
    for folder in (BUILD_DIR, DIST_DIR):
        if folder.exists():
            try:
                shutil.rmtree(folder)
                print(f"   Removed: {folder.name}/")
            except Exception as e:
                print(f"   Warning: Could not remove {folder}: {e}")


def stage_distribution_files() -> None:
    print("\n>> Staging distribution assets...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Copy config.yaml template next to the executable for easy user editing
    src_config = ROOT_DIR / "config.yaml"
    dst_config = OUTPUT_DIR / "config.yaml"
    if src_config.exists() and not dst_config.exists():
        shutil.copy2(src_config, dst_config)
        print("   Copied: config.yaml to distribution folder.")

    # Create empty screenshots folder
    (OUTPUT_DIR / "screenshots").mkdir(exist_ok=True)


def verify_build() -> bool:
    print("\n>> Verifying build output...")
    if not EXE_FILE.exists():
        print(f"❌ Build verification failed: Executable not found at {EXE_FILE}")
        return False

    size_mb = EXE_FILE.stat().st_size / (1024 * 1024)
    print(f"✅ Success! Executable created: {EXE_FILE.name} ({size_mb:.2f} MB)")
    print(f"   Full distribution path: {OUTPUT_DIR}")
    return True


def main() -> None:
    print("==================================================")
    print("   Liny Desktop AI - Standalone Packaging Pipeline")
    print("==================================================")

    # Step 1: Pre-build test
    print("\n[Step 1/4] Running pre-build validation tests...")
    test_script = ROOT_DIR / "tests" / "test_packaging.py"
    if not run_command([sys.executable, str(test_script)]):
        print("❌ Pre-build packaging checks failed! Aborting build.")
        sys.exit(1)

    # Step 2: Clean old builds
    print("\n[Step 2/4] Cleaning workspace...")
    clean_artifacts()

    # Step 3: Run PyInstaller
    print("\n[Step 3/4] Running PyInstaller standalone bundling...")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC_FILE)]
    if not run_command(cmd):
        print("❌ PyInstaller compilation encountered errors.")
        sys.exit(1)

    # Step 4: Stage & verify
    print("\n[Step 4/4] Staging and verifying executable...")
    stage_distribution_files()
    if verify_build():
        print("\n🎉 Packaging completed successfully!")
        print(f"   To run your standalone assistant: {EXE_FILE}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()

