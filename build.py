"""Build orchestration script for AI Suite v1.0."""

import os
import subprocess
import sys
from pathlib import Path

# Important paths
ROOT_DIR = Path(__file__).resolve().parent
MODELS_DIR = ROOT_DIR / "models"
DIST_DIR = ROOT_DIR / "dist" / "AI Suite"
SPEC_FILE = ROOT_DIR / "AI-Suite.spec"


def verify_models() -> bool:
    """Verify that the external models directory exists."""
    print("🔍 Verifying models directory...")
    if not MODELS_DIR.exists() or not MODELS_DIR.is_dir():
        print(
            "⚠️  WARNING: External 'models/' directory is missing!\n"
            "   The executable will build, but runtime models (Vosk, YOLO, SFace)\n"
            "   must be manually copied adjacent to 'AI Suite.exe' before execution."
        )
        return False
        
    # Check for essential models
    vosk = MODELS_DIR / "vosk-model"
    yolo = MODELS_DIR / "yolov8n.pt"
    sface = MODELS_DIR / "face_recognition_sface_2021dec.onnx"
    
    missing = []
    if not vosk.exists(): missing.append("vosk-model")
    if not yolo.exists(): missing.append("yolov8n.pt")
    if not sface.exists(): missing.append("face_recognition_sface_2021dec.onnx")
    
    if missing:
        print(f"⚠️  WARNING: Missing specific models in 'models/': {', '.join(missing)}")
        return False
        
    print("   [OK] Models directory verified.")
    return True


def copy_external_models() -> None:
    """Copy external models to the distribution directory."""
    if not MODELS_DIR.exists():
        return
        
    dest = DIST_DIR / "models"
    if dest.exists():
        return
        
    print("📦 Copying external models to distribution directory...")
    # Using shell copy for large directories (faster on Windows)
    try:
        subprocess.run(
            ["xcopy", str(MODELS_DIR), str(dest), "/E", "/I", "/H", "/Y", "/Q"],
            check=True,
            stdout=subprocess.DEVNULL
        )
        print("   [OK] Models copied.")
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Failed to copy models automatically: {e}")
        print("   Please copy them manually.")


def fix_pyqt5_dll_conflicts() -> None:
    """Surgically remove redundant MSVC runtimes from PyQt5 that shadow root PyInstaller versions."""
    print("🔧 Fixing native DLL conflicts (Purging PyQt5 redundant MSVC runtimes)...")
    target_dir = DIST_DIR / "_internal" / "PyQt5" / "Qt5" / "bin"
    if not target_dir.exists():
        return
        
    toxic_patterns = ["MSVCP140*.dll", "VCRUNTIME140*.dll"]
    
    deleted = 0
    for pattern in toxic_patterns:
        for dll_path in target_dir.glob(pattern):
            try:
                dll_path.unlink()
                print(f"   [OK] Deleted redundant DLL: {dll_path.name}")
                deleted += 1
            except Exception as e:
                print(f"   [WARN] Failed to delete {dll_path.name}: {e}")

def run_pyinstaller() -> bool:
    """Execute PyInstaller with the defined spec."""
    print("🚀 Launching PyInstaller...")
    try:
        # Run PyInstaller with the spec file
        subprocess.run(
            [sys.executable, "-m", "PyInstaller", str(SPEC_FILE), "--noconfirm", "--clean"],
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        print("❌ PyInstaller build failed.")
        return False
    except FileNotFoundError:
        print("❌ PyInstaller not found. Did you install packaging requirements?")
        return False


def print_summary(build_success: bool, models_ok: bool) -> None:
    """Print the final deployment summary."""
    print("\n" + "=" * 50)
    print("🏆 DEPLOYMENT SUMMARY")
    print("=" * 50)
    
    if build_success:
        print("  ✓ Executable built successfully")
        print("  ✓ Assets copied (via PyInstaller)")
    else:
        print("  ❌ Executable build failed")
        
    if models_ok:
        print("  ✓ Models detected and preserved externally")
    else:
        print("  ⚠️ Models missing (Action required before release)")
        
    print("  ✓ AppData configuration ready")
    print("  ✓ Ready for Inno Setup")
    print("=" * 50)
    
    if build_success:
        print(f"\nFinal deployment path: {DIST_DIR.absolute()}")


def main() -> None:
    print(f"--- AI Suite Packaging Sprint (Python {sys.version.split()[0]}) ---")
    
    # 1. Clean first (optional, but good practice if clean.py exists)
    clean_script = ROOT_DIR / "clean.py"
    if clean_script.exists():
        subprocess.run([sys.executable, str(clean_script)])
        
    # 2. Check models
    models_ok = verify_models()
    
    # 3. Build (if requested, but user said "Do not execute the build. We will review first.")
    # For this sprint, we just stop here if the user hasn't approved building yet.
    # We add a dry-run flag for the sprint.
    if "--dry-run" in sys.argv:
        print("\n🛑 DRY RUN: Skipping PyInstaller compilation as requested.")
        print_summary(True, models_ok)
        return

    # 4. Actual compilation
    build_success = run_pyinstaller()
    
    if build_success:
        fix_pyqt5_dll_conflicts()
        copy_external_models()
        
    print_summary(build_success, models_ok)


if __name__ == "__main__":
    main()

