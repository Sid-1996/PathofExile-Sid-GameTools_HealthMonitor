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

APP_VERSION = "1.0.8"

class GameToolBuilder:
    def __init__(self):
        self.project_dir = os.path.dirname(os.path.dirname(__file__))
        # Canonical source directory.
        self.src_dir = os.path.join(self.project_dir, "src")
        # Backward-compatible source directory used by older workflows.
        self.compat_src_dir = os.path.join(self.project_dir, "src for DEVELOPER")
        self.tools_dir = os.path.join(self.project_dir, "tools")
        self.build_dir = os.path.join(self.project_dir, "build")
        self.dist_dir = os.path.join(self.project_dir, "dist")

        self.icon_file = os.path.join(self.tools_dir, "GameTools_HealthMonitor.ico")

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
        self.log(f"??: {step_name}")

    def end_step(self, step_name):
        if step_name in self.step_times:
            duration = datetime.now() - self.step_times[step_name]
            minutes = duration.total_seconds() / 60
            self.log(f"摰?: {step_name} (??: {minutes:.1f} ??)")

    def check_dependencies(self):
        """瑼Ｘ靘陷"""
        self.log("瑼Ｘ靘陷...")
        required_packages = ["PyInstaller"]

        for package in required_packages:
            try:
                __import__("PyInstaller")
                self.log(f"{package} available")
            except ImportError:
                self.log(f"{package} missing")
                return False

        self.log("?????鞈游歇皛輯雲")
        return True

    def build_main_tool(self):
        """瑽遣銝餃極??- 雿輻摰靘陷??"""
        source_file = self._first_existing_path(
            os.path.join(self.src_dir, "health_monitor.py"),
            os.path.join(self.compat_src_dir, "health_monitor.py"),
        )
        if not os.path.exists(source_file):
            self.log("health_monitor.py not found")
            return False

        language_pack_file = self._first_existing_path(
            os.path.join(self.src_dir, "language_packs.json"),
            os.path.join(self.compat_src_dir, "language_packs.json"),
        )
        auto_click_exe_file = self._first_existing_path(
            os.path.join(self.src_dir, "auto_click.exe"),
            os.path.join(self.compat_src_dir, "auto_click.exe"),
        )

        package_dir = os.path.join(self.dist_dir, "GameTools_Package")
        os.makedirs(package_dir, exist_ok=True)
        run_tag = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        work_path = os.path.join(self.build_dir, f"pyinstaller_work_{run_tag}")
        spec_path = os.path.join(self.build_dir, "pyinstaller_specs")
        os.makedirs(work_path, exist_ok=True)
        os.makedirs(spec_path, exist_ok=True)

        try:
            # ?萄遣摰??PyInstaller ?賭誘嚗Ⅱ靽???鞈湧鋡怠???
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--noconsole",  # ?梯??賭誘閬?嚗憿舐內GUI
                "--noconfirm",
                "--workpath", work_path,
                "--specpath", spec_path,
                "--name", "GameTools_HealthMonitor",
                "--icon", self.icon_file,
                # ?詨?靘陷
                "--hidden-import", "PIL",
                "--hidden-import", "PIL.Image",
                "--hidden-import", "PIL.ImageTk",
                "--hidden-import", "PIL.ImageDraw",
                "--hidden-import", "PIL._imaging",
                "--copy-metadata", "Pillow",
                "--collect-data", "PIL",
                # OpenCV
                "--hidden-import", "cv2",
                "--collect-data", "cv2",
                # NumPy
                "--hidden-import", "numpy",
                # 蝟餌絞撌亙
                "--hidden-import", "mss",
                "--hidden-import", "keyboard",
                "--hidden-import", "pygetwindow",
                "--hidden-import", "pyautogui",
                "--hidden-import", "psutil",
                "--hidden-import", "psutil._psutil_windows",
                "--hidden-import", "psutil._pswindows",
                # Windows ?孵?璅∠? (?冽雿輻??餈質馱)
                "--hidden-import", "winreg",
                "--hidden-import", "ctypes",
                "--hidden-import", "ctypes.wintypes",
                # 蝬脰楝隢?
                "--hidden-import", "requests",
                "--hidden-import", "urllib3",
                # PyAutoGUI 摮?鞈?
                "--hidden-import", "pymsgbox",
                "--hidden-import", "pytweening",
                "--hidden-import", "pyscreeze",
                "--hidden-import", "mouseinfo",
                # Tkinter
                "--hidden-import", "tkinter",
                "--hidden-import", "tkinter.ttk",
                "--hidden-import", "tkinter.messagebox",
                "--hidden-import", "_tkinter",
                "--collect-data", "tkinter",
                # ?嗡??航?箸???鞈?
                "--hidden-import", "webbrowser",
                "--hidden-import", "win32gui",
                "--hidden-import", "traceback",
                "--collect-data", "pywin32",
                # ?豢?瑼?
                "--add-data", f"{os.path.join(self.project_dir, 'scripts', 'auto_click.ahk')};.",
                source_file
            ]

            if auto_click_exe_file:
                cmd.extend(["--add-data", f"{auto_click_exe_file};."])
            if language_pack_file:
                cmd.extend(["--add-data", f"{language_pack_file};."])

            # 瘛餃? Tkinter ??Pillow 鈭脖?瑼?
            self._add_binary_dependencies(cmd)

            self.log(f"?瑁? PyInstaller ?賭誘...")
            self.log(f"撌乩??桅?: {self.project_dir}")

            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                self.log(f"??PyInstaller 憭望?: {result.stderr}")
                return False

            # 蝘餃? exe ??package ?桅?
            self._move_exe_to_package(package_dir)

            self.log("Main tool build completed")
            return True

        except Exception as e:
            self.log(f"??瑽遣憭望?: {e}")
            return False

    def _add_binary_dependencies(self, cmd):
        """瘛餃?鈭脖?靘陷"""
        try:
            # Tkinter DLL
            python_home = os.path.normpath(sys.exec_prefix)
            dlls_dir = os.path.join(python_home, 'DLLs')
            for dll in ['tcl86t.dll', 'tk86t.dll', '_tkinter.pyd']:
                dll_path = os.path.join(dlls_dir, dll)
                if os.path.exists(dll_path):
                    cmd.extend(["--add-binary", f"{dll_path};."])

            # Tcl 鞈?
            tcl_base = os.path.join(python_home, 'tcl')
            if os.path.exists(tcl_base):
                cmd.extend(["--add-data", f"{tcl_base};tcl"])

            # Pillow 鈭脖?瑼?
            try:
                import PIL
                pil_dir = os.path.dirname(PIL.__file__)
                pillow_pyds = [
                    '_imaging.cp310-win_amd64.pyd',
                    '_imagingtk.cp310-win_amd64.pyd',
                    '_imagingmath.cp310-win_amd64.pyd',
                    '_imagingft.cp310-win_amd64.pyd',
                    '_imagingcms.cp310-win_amd64.pyd',
                    '_imagingmorph.cp310-win_amd64.pyd'
                ]
                for pyd in pillow_pyds:
                    pyd_path = os.path.join(pil_dir, pyd)
                    if os.path.exists(pyd_path):
                        cmd.extend(["--add-binary", f"{pyd_path};PIL"])
            except Exception as e:
                self.log(f"?? Pillow 鈭脖?瑼?瘛餃?憭望?: {e}")

            # OpenCV 鈭脖?瑼?
            try:
                import cv2
                cv2_dir = os.path.dirname(cv2.__file__)
                cv2_pyd = os.path.join(cv2_dir, 'cv2.pyd')
                if os.path.exists(cv2_pyd):
                    cmd.extend(["--add-binary", f"{cv2_pyd};cv2"])
            except Exception as e:
                self.log(f"?? OpenCV 鈭脖?瑼?瘛餃?憭望?: {e}")

        except Exception as e:
            self.log(f"?? 瘛餃?鈭脖?靘陷憭望?: {e}")

    def _move_exe_to_package(self, package_dir):
        """蝘餃? exe ??package ?桅?"""
        possible_sources = [
            os.path.join(self.dist_dir, "GameTools_HealthMonitor.exe"),
            os.path.join(self.dist_dir, "GameTools_HealthMonitor", "GameTools_HealthMonitor.exe")
        ]

        for src in possible_sources:
            if os.path.exists(src):
                dst = os.path.join(package_dir, "GameTools_HealthMonitor.exe")
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(src, dst)
                self.log(f"??蝘餃? exe: {dst}")
                break

    def create_installation_package(self):
        """Create installation package."""
        package_dir = os.path.join(self.dist_dir, "GameTools_Package")

        # 銴ˊ敹?瑼?
        files_to_copy = [
            (
                self._first_existing_path(
                    os.path.join(self.src_dir, "auto_click.exe"),
                    os.path.join(self.compat_src_dir, "auto_click.exe"),
                ),
                "auto_click.exe",
            ),
            (
                self._first_existing_path(
                    os.path.join(self.src_dir, "雿輻隤芣?.md"),
                    os.path.join(self.compat_src_dir, "雿輻隤芣?.md"),
                ),
                "雿輻隤芣?.md",
            ),
            (
                self._first_existing_path(
                    os.path.join(self.src_dir, "language_packs.json"),
                    os.path.join(self.compat_src_dir, "language_packs.json"),
                ),
                "language_packs.json",
            ),
        ]

        for src_path, dst_name in files_to_copy:
            dst_full = os.path.join(package_dir, dst_name)

            if os.path.exists(src_path):
                shutil.copy2(src_path, dst_full)
                self.log(f"??銴ˊ: {dst_name}")

        # ?萄遣??撌亙.bat
        bat_content = '''@echo off
chcp 65001 >nul
echo 甇??? PathofExile Sid Sid頛撌亙...
echo.
echo 隢誑蝞∠??⊥???銵迨撌亙隞亦敺?雿喲?撽?
echo.
start "" "GameTools_HealthMonitor.exe"
'''

        bat_path = os.path.join(package_dir, "??撌亙.bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        self.log("???萄遣??撌亙.bat")

        # ?萄遣 README.txt
        readme_content = f"""# Sid Game Tools

## Quick Start
1. Run `GameTools_HealthMonitor.exe`.
2. If Windows prompts for permission, allow the app to run.
3. See the included documentation file for setup guidance.

## Package Contents
- GameTools_HealthMonitor.exe
- auto_click.exe
- language_packs.json
- README.txt

## Version
- Version: {APP_VERSION}
- Build time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Notes
- This package is intended for local Windows use.
- Keep the bundled files together in the same folder.
- Do not remove language or helper executable files from the package.
"""

        readme_path = os.path.join(package_dir, "README.txt")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        self.log("???萄遣README.txt")

        # =============================================================================
        # ? ?蝯?鋆??批捆閬? (IMPORTANT - DO NOT MODIFY)
        # =============================================================================
        # 憯葬瑼??????府?芸??思誑銝?隞塚?隢瘛餃???支遙雿?隞塚?
        #
        # ??敹????隞?
        #   ??auto_click.exe              (AutoHotkey?芸?暺?撌亙)
        #   ??GameTools_HealthMonitor.exe (銝餌?撘?瑁??辣)
        #   ??language_packs.json         (隤???蝵?
        #   ??README.txt                  (雿輻隤芣?)
        #   ??雿輻隤芣?.md                 (閰喟敦隤芣???)
        #   ????撌亙.bat               (???單)
        #
        # ??蝳迫???隞?
        #   ??screenshots/                (????嚗?????)
        #   ??health_monitor_config.json  (?冽?蔭嚗?????)
        #   ??隞颱??嗡??冽??葫閰行?隞?
        #
        # 靽格甇日?頛臬?隢?蝝啗?隡啣蔣?選?
        # =============================================================================

        # ?萄遣 ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        zip_name = f"GameTools_HealthMonitor_v{APP_VERSION}_{timestamp}"
        zip_path = os.path.join(self.dist_dir, zip_name)

        shutil.make_archive(zip_path, 'zip', package_dir)
        self.log(f"???萄遣摰??? {zip_name}.zip")

        return True

    def build_all(self):
        """?瑁?摰瑽遣"""
        self.log("?? ??瑽遣 Sid頛撌亙 - 摰靽桀儔?")

        try:
            steps = [
                ("靘陷瑼Ｘ", self.check_dependencies),
                ("Build main tool", self.build_main_tool),
                ("Create package", self.create_installation_package)
            ]

            for step_name, step_func in steps:
                self.start_step(step_name)
                if not step_func():
                    self.log(f"??瑽遣憭望??? {step_name}")
                    return False
                self.end_step(step_name)

            total_time = datetime.now() - self.start_time
            minutes = total_time.total_seconds() / 60
            self.log(f"? 蝮質?: {minutes:.1f} ??")
            self.log("Build completed successfully")
            self.log("? 摰?????dist/ ?桅?")

            return True

        except Exception as e:
            self.log(f"??瑽遣?啣虜: {e}")
            return False

def main():
    builder = GameToolBuilder()
    success = builder.build_all()
    # input("\n?遙?蝯?...")  # 蝘駁隞交??鈭??啣?
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
