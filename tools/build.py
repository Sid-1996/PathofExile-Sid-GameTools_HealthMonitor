#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GameTools Health Monitor - Build Script
Builds GameTools_HealthMonitor.exe via PyInstaller and assembles the release package.
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

# Add src to path to import version
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
from _version import __version__

APP_VERSION = __version__


class GameToolBuilder:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        # Canonical source directory.
        self.src_dir = os.path.join(self.project_dir, "src")
        self.tools_dir = os.path.join(self.project_dir, "tools")
        self.build_dir = os.path.join(self.project_dir, "build")
        self.dist_dir = os.path.join(self.project_dir, "dist")

        self.icon_file = os.path.join(self.tools_dir, "GameTools_HealthMonitor.ico")
        # 93f3eeb 把 icon 移到 assets/，兩處皆支援
        self.icon_file = self._first_existing_path(
            self.icon_file,
            os.path.join(self.project_dir, "assets", "GameTools_HealthMonitor.ico"),
        ) or os.path.join(self.tools_dir, "GameTools_HealthMonitor.ico")

        self.start_time = datetime.now()
        self.step_times = {}

        os.makedirs(self.build_dir, exist_ok=True)
        os.makedirs(self.dist_dir, exist_ok=True)

    def _first_existing_path(self, *candidates):
        """Return the first existing path from candidates, else None."""
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {message}"
        try:
            print(line)
        except UnicodeEncodeError:
            # Fallback for Windows consoles using legacy encodings (e.g. cp950).
            encoding = sys.stdout.encoding or "utf-8"
            safe_line = line.encode(encoding, errors="replace").decode(encoding, errors="replace")
            print(safe_line)

    def start_step(self, step_name):
        self.step_times[step_name] = datetime.now()
        self.log(f"Step: {step_name}")

    def end_step(self, step_name):
        if step_name in self.step_times:
            duration = datetime.now() - self.step_times[step_name]
            minutes = duration.total_seconds() / 60
            self.log(f"Done: {step_name} ({minutes:.1f} min)")

    def check_dependencies(self):
        """Check build dependencies"""
        self.log("Checking dependencies...")
        required_packages = ["PyInstaller"]

        for package in required_packages:
            try:
                __import__("PyInstaller")
                self.log(f"{package} available")
            except ImportError:
                self.log(f"{package} missing")
                return False

        self.log("All dependencies available")
        return True

    def build_main_tool(self):
        """Build the main GameTools_HealthMonitor executable."""
        source_file = os.path.join(self.src_dir, "app.py")
        if not os.path.exists(source_file):
            self.log("app.py not found")
            return False

        language_pack_file = os.path.join(self.src_dir, "language_packs.json")
        auto_click_exe_file = os.path.join(self.src_dir, "auto_click.exe")

        package_dir = os.path.join(self.dist_dir, "GameTools_Package")
        os.makedirs(package_dir, exist_ok=True)
        run_tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        work_path = os.path.join(self.build_dir, f"pyinstaller_work_{run_tag}")
        spec_path = os.path.join(self.build_dir, "pyinstaller_specs")
        os.makedirs(work_path, exist_ok=True)
        os.makedirs(spec_path, exist_ok=True)

        try:
            # Build PyInstaller command for the main executable
            cmd = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onedir",
                "--noconsole",  # No console window for GUI app
                "--noconfirm",
                "--workpath",
                work_path,
                "--specpath",
                spec_path,
                "--name",
                "GameTools_HealthMonitor",
                "--icon",
                self.icon_file,
                # Bootloader splash（Python 啟動前即顯示，覆蓋 import 空窗）
                "--splash",
                os.path.join(self.project_dir, "assets", "PoeSidTools.png"),
                # Hidden imports
                "--hidden-import",
                "PIL",
                "--hidden-import",
                "PIL.Image",
                "--hidden-import",
                "PIL.ImageDraw",
                "--hidden-import",
                "PIL._imaging",
                "--copy-metadata",
                "Pillow",
                # OpenCV
                "--hidden-import",
                "cv2",
                # NumPy
                "--hidden-import",
                "numpy",
                # Automation libs
                "--hidden-import",
                "mss",
                "--hidden-import",
                "keyboard",
                "--hidden-import",
                "pygetwindow",
                "--hidden-import",
                "pyautogui",
                "--hidden-import",
                "pyperclip",
                "--hidden-import",
                "psutil",
                "--hidden-import",
                "psutil._psutil_windows",
                "--hidden-import",
                "psutil._pswindows",
                # Windows API (screen capture helpers)
                "--hidden-import",
                "winreg",
                "--hidden-import",
                "ctypes",
                "--hidden-import",
                "ctypes.wintypes",
                # HTTP / network
                "--hidden-import",
                "requests",
                "--hidden-import",
                "urllib3",
                # PyAutoGUI deps
                "--hidden-import",
                "pymsgbox",
                "--hidden-import",
                "pytweening",
                "--hidden-import",
                "pyscreeze",
                "--hidden-import",
                "mouseinfo",
                # PySide6 + qfluentwidgets（Phase 1 實測：只需 --collect-all qfluentwidgets，
                # 絕不加 --exclude-module PySide6.*，會打斷 hook 的 plugin/qt.conf 處理）
                "--collect-all",
                "qfluentwidgets",
                # Windows.Graphics.Capture（Rust native extension，背景截圖）
                "--collect-all",
                "windows_capture",
                # Misc
                "--hidden-import",
                "webbrowser",
                "--hidden-import",
                "win32gui",
                "--hidden-import",
                "traceback",
                # 排除與本專案無關的大型套件（來自其他專案的環境污染）
                "--exclude-module",
                "torch",
                "--exclude-module",
                "torchvision",
                "--exclude-module",
                "torchaudio",
                "--exclude-module",
                "torch_lightning",
                "--exclude-module",
                "onnxruntime",
                "--exclude-module",
                "onnx",
                "--exclude-module",
                "pandas",
                "--exclude-module",
                "scipy",
                "--exclude-module",
                "matplotlib",
                "--exclude-module",
                "sklearn",
                "--exclude-module",
                "transformers",
                # Data files
                "--paths",
                self.src_dir,
                source_file,
            ]

            # 旁置資源（language_packs.json / auto_click.exe / auto_click.ahk）
            # 一律由 create_installation_package 複製到 exe 旁，不塞進 _internal/
            if os.path.exists(auto_click_exe_file):
                self.log(f"Sidecar: auto_click.exe ({os.path.getsize(auto_click_exe_file)} bytes)")
            else:
                self.log("WARNING: auto_click.exe not found in src/, skipping")
            if language_pack_file and os.path.exists(language_pack_file):
                self.log(f"Sidecar: language_packs.json ({os.path.getsize(language_pack_file)} bytes)")
            else:
                self.log("WARNING: language_packs.json not found in src/, skipping")

            # Collect binary dependencies (Tkinter, Pillow, OpenCV)
            self._add_binary_dependencies(cmd)

            self.log("Running PyInstaller...")
            self.log(f"Build dir: {self.project_dir}")

            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")

            if result.returncode != 0:
                self.log(f"PyInstaller error: {result.stderr}")
                return False

            # Move exe to package
            self._move_exe_to_package(package_dir)

            self.log("Main tool build completed")
            return True

        except Exception as e:
            self.log(f"Build failed: {e}")
            return False

    def _add_binary_dependencies(self, cmd):
        """Collect binary dependencies (DLLs, pyds)"""
        try:
            # Pillow binary modules
            try:
                import PIL
                import sysconfig

                pil_dir = os.path.dirname(PIL.__file__)
                ext_suffix = sysconfig.get_config_var("EXT_SUFFIX") or ".cp312-win_amd64.pyd"
                pillow_pyds = [f"_imaging{ext_suffix}", f"_imagingmath{ext_suffix}", f"_imagingft{ext_suffix}", f"_imagingcms{ext_suffix}", f"_imagingmorph{ext_suffix}"]
                for pyd in pillow_pyds:
                    pyd_path = os.path.join(pil_dir, pyd)
                    if os.path.exists(pyd_path):
                        cmd.extend(["--add-binary", f"{pyd_path};PIL"])
            except Exception as e:
                self.log(f"Failed to collect Pillow binaries: {e}")

            # OpenCV binary modules
            try:
                import cv2

                cv2_dir = os.path.dirname(cv2.__file__)
                cv2_pyd = os.path.join(cv2_dir, "cv2.pyd")
                if os.path.exists(cv2_pyd):
                    cmd.extend(["--add-binary", f"{cv2_pyd};cv2"])
            except Exception as e:
                self.log(f"Failed to collect OpenCV binaries: {e}")

        except Exception as e:
            self.log(f"Failed to collect binary dependencies: {e}")

    def _move_exe_to_package(self, package_dir):
        """Move built onedir tree (exe + _internal/) into package directory"""
        onedir_src = os.path.join(self.dist_dir, "GameTools_HealthMonitor")
        onefile_src = os.path.join(self.dist_dir, "GameTools_HealthMonitor.exe")

        # onedir: move the whole tree so exe + _internal/ stay together
        if os.path.isdir(onedir_src):
            for item in os.listdir(onedir_src):
                src = os.path.join(onedir_src, item)
                dst = os.path.join(package_dir, item)
                if os.path.exists(dst):
                    if os.path.isdir(dst):
                        shutil.rmtree(dst)
                    else:
                        os.remove(dst)
                shutil.move(src, dst)
                self.log(f"Moved onedir item: {item}")
            os.rmdir(onedir_src)
            return

        # legacy onefile: move the single exe
        if os.path.exists(onefile_src):
            dst = os.path.join(package_dir, "GameTools_HealthMonitor.exe")
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(onefile_src, dst)
            self.log(f"Moved exe: {dst}")

    def build_updater(self):
        """Build updater_main.py → updater.exe (lightweight, no GUI deps)."""
        source_file = os.path.join(self.project_dir, "updater_main.py")
        if not os.path.exists(source_file):
            self.log("updater_main.py not found, skipping updater build")
            return True

        package_dir = os.path.join(self.dist_dir, "GameTools_Package")
        run_tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        work_path = os.path.join(self.build_dir, f"pyinstaller_updater_{run_tag}")
        spec_path = os.path.join(self.build_dir, "pyinstaller_specs")
        os.makedirs(work_path, exist_ok=True)
        os.makedirs(spec_path, exist_ok=True)

        try:
            cmd = [
                sys.executable,
                "-m",
                "PyInstaller",
                "--onefile",
                "--console",
                "--noconfirm",
                "--workpath",
                work_path,
                "--specpath",
                spec_path,
                "--name",
                "updater",
                "--distpath",
                self.dist_dir,
                source_file,
            ]

            self.log("Building updater.exe...")
            result = subprocess.run(cmd, cwd=self.project_dir, capture_output=True, text=True, encoding="utf-8", errors="replace")

            if result.returncode != 0:
                self.log(f"PyInstaller updater error: {result.stderr}")
                return False

            updater_src = os.path.join(self.dist_dir, "updater.exe")
            if os.path.exists(updater_src):
                updater_dst = os.path.join(package_dir, "updater.exe")
                if os.path.exists(updater_dst):
                    os.remove(updater_dst)
                shutil.move(updater_src, updater_dst)
                self.log(f"Built updater.exe → {updater_dst}")
            else:
                self.log("WARNING: updater.exe not found in dist/")
                return False

            return True

        except Exception as e:
            self.log(f"Updater build failed: {e}")
            return False

    def create_installation_package(self):
        """Create installation package."""
        package_dir = os.path.join(self.dist_dir, "GameTools_Package")

        # Copy release assets
        files_to_copy = [
            (
                os.path.join(self.src_dir, "auto_click.exe"),
                "auto_click.exe",
            ),
            (
                os.path.join(self.project_dir, "scripts", "auto_click.ahk"),
                "auto_click.ahk",
            ),
            (
                os.path.join("docs", "使用說明.md"),
                "使用說明.md",
            ),
            (
                os.path.join(self.src_dir, "language_packs.json"),
                "language_packs.json",
            ),
            (
                os.path.join(self.dist_dir, "GameTools_Package", "updater.exe"),
                "updater.exe",
            ),
        ]

        for src_path, dst_name in files_to_copy:
            dst_full = os.path.join(package_dir, dst_name)

            if os.path.exists(src_path):
                if os.path.abspath(src_path) == os.path.abspath(dst_full):
                    self.log(f"Skipped (same path): {dst_name}")
                else:
                    shutil.copy2(src_path, dst_full)
                    self.log(f"Copied: {dst_name}")
            else:
                self.log(f"WARNING: {src_path} not found, skipping {dst_name}")

        # Create launch bat
        bat_content = r"""@echo off
chcp 65001 >nul
title GameTools Health Monitor

:restart
echo [INFO] 啟動 GameTools Health Monitor...
start /WAIT "" "%~dp0GameTools_HealthMonitor.exe"

if exist "%~dp0restart.flag" (
    del "%~dp0restart.flag"
    echo [INFO] 偵測到重啟標記，重新啟動...
    goto restart
)

echo [INFO] 工具已結束。
pause
"""

        bat_path = os.path.join(package_dir, "啟動工具.bat")
        with open(bat_path, "w", encoding="utf-8") as f:
            f.write(bat_content)
        self.log("Created 啟動工具.bat")

        # Create README.txt
        readme_content = f"""# Sid Game Tools

## Quick Start
1. Run `GameTools_HealthMonitor.exe` or `啟動工具.bat`.
2. If Windows prompts for permission, allow the app to run.
3. See `使用說明.md` for detailed setup guidance.

## Package Contents
- GameTools_HealthMonitor.exe (main app)
- _internal/ (runtime dependencies, keep next to the exe)
- updater.exe (auto-update helper)
- auto_click.exe (auto-click helper)
- auto_click.ahk (auto-click script fallback)
- language_packs.json (language strings)
- 使用說明.md (user documentation)
- 啟動工具.bat (launcher)

## Auto-Update
The app checks for new versions on startup. When an update is available,
a notification will appear. Click "Download Now" to update automatically.

## Version
- Version: {APP_VERSION}
- Build time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Notes
- Keep all files together in the same folder.
- Do not remove _internal/, language_packs.json or auto_click.exe.
"""

        readme_path = os.path.join(package_dir, "README.txt")
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)
        self.log("Created README.txt")

        # =============================================================================
        # Package structure notes (IMPORTANT - DO NOT MODIFY)
        # =============================================================================
        # The release ZIP contains:
        #   GameTools_HealthMonitor.exe (Main application, PyInstaller onedir)
        #   _internal/                  (onedir 相依樹，需與 exe 同資料夾)
        #   auto_click.exe              (AutoHotkey auto-clicker)
        #   auto_click.ahk              (AutoHotkey script fallback)
        #   updater.exe                 (Auto-update helper)
        #   language_packs.json         (Language strings)
        #   README.txt                  (Quick start)
        #   使用說明.md                 (User documentation)
        #   啟動工具.bat                (Launcher)
        #
        # Runtime-generated files excluded from ZIP:
        #   screenshots/                (Captured during use)
        #   health_monitor_config.json  (User settings)
        #   health_monitor_config.json.backup (Auto-backup)
        #
        # When changing packaged files, update both the copy list above
        # and this comment block to stay in sync.
        # =============================================================================

        # Create ZIP
        # 壓 ZIP 前清理執行期殘留（使用者個人設定/截圖）
        for item_name in ["health_monitor_config.json", "health_monitor_config.json.backup", "screenshots"]:
            item_path = os.path.join(package_dir, item_name)
            if os.path.isfile(item_path):
                os.remove(item_path)
                self.log(f"Cleaned residue: {item_name}")
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                self.log(f"Cleaned residue: {item_name}/")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        zip_name = f"GameTools_HealthMonitor_v{APP_VERSION}_{timestamp}"
        zip_path = os.path.join(self.dist_dir, zip_name)

        shutil.make_archive(zip_path, "zip", package_dir)
        self.log(f"Created ZIP: {zip_name}.zip")

        return True

    def build_all(self):
        """Run full build pipeline"""
        self.log("=== Build Sid GameTools Health Monitor - Full Pipeline ===")

        try:
            steps = [
                ("Check Dependencies", self.check_dependencies),
                ("Build main tool", self.build_main_tool),
                ("Build updater", self.build_updater),
                ("Create package", self.create_installation_package),
            ]

            for step_name, step_func in steps:
                self.start_step(step_name)
                if not step_func():
                    self.log(f"Build failed at step: {step_name}")
                    return False
                self.end_step(step_name)

            # 清理 PyInstaller 暫存檔
            self.start_step("Cleanup build residue")
            if os.path.exists(self.build_dir):
                shutil.rmtree(self.build_dir)
                self.log("build/ removed")
            self.end_step("Cleanup build residue")

            total_time = datetime.now() - self.start_time
            minutes = total_time.total_seconds() / 60
            self.log(f"Total build time: {minutes:.1f} min")
            self.log("Build completed successfully")
            self.log("Output ZIP in dist/")

            return True

        except Exception as e:
            self.log(f"Build pipeline error: {e}")
            return False


def main():
    builder = GameToolBuilder()
    success = builder.build_all()
    # input("\nPress Enter to exit...")  # Uncomment to pause before exit
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
