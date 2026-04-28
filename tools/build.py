#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自動化構建和打包腳本 - 完整修復版本
確保 exe 重啟功能正常，並打包所有必要依賴
"""

import os
import sys
import subprocess
import shutil
from datetime import datetime

APP_VERSION = "1.0.7"

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
        self.log(f"開始: {step_name}")

    def end_step(self, step_name):
        if step_name in self.step_times:
            duration = datetime.now() - self.step_times[step_name]
            minutes = duration.total_seconds() / 60
            self.log(f"完成: {step_name} (耗時: {minutes:.1f} 分鐘)")

    def check_dependencies(self):
        """檢查依賴"""
        self.log("檢查依賴...")
        required_packages = ["PyInstaller"]

        for package in required_packages:
            try:
                __import__("PyInstaller")
                self.log(f"✅ {package} 已安裝")
            except ImportError:
                self.log(f"❌ {package} 未安裝")
                return False

        self.log("✅ 所有依賴已滿足")
        return True

    def build_main_tool(self):
        """構建主工具 - 使用完整依賴打包"""
        source_file = self._first_existing_path(
            os.path.join(self.src_dir, "health_monitor.py"),
            os.path.join(self.compat_src_dir, "health_monitor.py"),
        )
        if not os.path.exists(source_file):
            self.log("❌ health_monitor.py 不存在")
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

        try:
            # 創建完整的 PyInstaller 命令，確保所有依賴都被包含
            cmd = [
                sys.executable, "-m", "PyInstaller",
                "--onefile",
                "--noconsole",  # 隱藏命令視窗，只顯示GUI
                "--clean",
                "--name", "GameTools_HealthMonitor",
                "--icon", self.icon_file,
                # 核心依賴
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
                # 系統工具
                "--hidden-import", "mss",
                "--hidden-import", "keyboard",
                "--hidden-import", "pygetwindow",
                "--hidden-import", "pyautogui",
                "--hidden-import", "psutil",
                "--hidden-import", "psutil._psutil_windows",
                "--hidden-import", "psutil._pswindows",
                # Windows 特定模組 (用於使用時間追蹤)
                "--hidden-import", "winreg",
                "--hidden-import", "ctypes",
                "--hidden-import", "ctypes.wintypes",
                # 網路請求
                "--hidden-import", "requests",
                "--hidden-import", "urllib3",
                # PyAutoGUI 子依賴
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
                # 數據檔案
                "--add-data", f"{os.path.join(self.project_dir, 'scripts', 'auto_click.ahk')};.",
                source_file
            ]

            if auto_click_exe_file:
                cmd.extend(["--add-data", f"{auto_click_exe_file};."])
            if language_pack_file:
                cmd.extend(["--add-data", f"{language_pack_file};."])

            # 添加 Tkinter 和 Pillow 二進位檔案
            self._add_binary_dependencies(cmd)

            self.log(f"執行 PyInstaller 命令...")
            self.log(f"工作目錄: {self.project_dir}")

            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            if result.returncode != 0:
                self.log(f"❌ PyInstaller 失敗: {result.stderr}")
                return False

            # 移動 exe 到 package 目錄
            self._move_exe_to_package(package_dir)

            self.log("✅ 主工具打包完成")
            return True

        except Exception as e:
            self.log(f"❌ 構建失敗: {e}")
            return False

    def _add_binary_dependencies(self, cmd):
        """添加二進位依賴"""
        try:
            # Tkinter DLL
            python_home = os.path.normpath(sys.exec_prefix)
            dlls_dir = os.path.join(python_home, 'DLLs')
            for dll in ['tcl86t.dll', 'tk86t.dll', '_tkinter.pyd']:
                dll_path = os.path.join(dlls_dir, dll)
                if os.path.exists(dll_path):
                    cmd.extend(["--add-binary", f"{dll_path};."])

            # Tcl 資料
            tcl_base = os.path.join(python_home, 'tcl')
            if os.path.exists(tcl_base):
                cmd.extend(["--add-data", f"{tcl_base};tcl"])

            # Pillow 二進位檔案
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
                self.log(f"⚠️ Pillow 二進位檔案添加失敗: {e}")

            # OpenCV 二進位檔案
            try:
                import cv2
                cv2_dir = os.path.dirname(cv2.__file__)
                cv2_pyd = os.path.join(cv2_dir, 'cv2.pyd')
                if os.path.exists(cv2_pyd):
                    cmd.extend(["--add-binary", f"{cv2_pyd};cv2"])
            except Exception as e:
                self.log(f"⚠️ OpenCV 二進位檔案添加失敗: {e}")

        except Exception as e:
            self.log(f"⚠️ 添加二進位依賴失敗: {e}")

    def _move_exe_to_package(self, package_dir):
        """移動 exe 到 package 目錄"""
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
                self.log(f"✅ 移動 exe: {dst}")
                break

    def create_installation_package(self):
        """創建安裝包"""
        package_dir = os.path.join(self.dist_dir, "GameTools_Package")

        # 複製必要檔案
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
                    os.path.join(self.src_dir, "使用說明.md"),
                    os.path.join(self.compat_src_dir, "使用說明.md"),
                ),
                "使用說明.md",
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
                self.log(f"✅ 複製: {dst_name}")

        # 創建啟動工具.bat
        bat_content = '''@echo off
chcp 65001 >nul
echo 正在啟動 PathofExile Sid Sid輔助工具...
echo.
echo 請以管理員權限運行此工具以獲得最佳體驗
echo.
start "" "GameTools_HealthMonitor.exe"
'''

        bat_path = os.path.join(package_dir, "啟動工具.bat")
        with open(bat_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)
        self.log("✅ 創建啟動工具.bat")

        # 創建 README.txt
        readme_content = f'''# Sid輔助工具

## 使用說明
1. 直接運行 GameTools_HealthMonitor.exe 即可開始使用
2. 無需額外安裝任何依賴，所有必要組件已內嵌
3. 首次使用建議閱讀使用說明.md了解各項功能

## 功能說明
- 血魔監控：智能監控血量魔力並自動使用藥水
- 快捷操作：F3清包、F5回城、F6取物等快捷功能
- 自動化操作：支持各種遊戲內自動化操作
- 完全免費開放，無任何使用限制

## 技術支持
本工具完全開源，源代碼可在專案庫中查看。
如有問題，請參考使用說明.md或查看源代碼。

## 版本資訊
- 版本：v{APP_VERSION}
- 構建時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 版本類型：無功能限制

## 重要聲明
- 本軟體是免費開源的。如果你被收費,請立即退款。請造訪 GitHub 下載最新的官方版本。
- 本軟體僅供個人使用,用於學習Python 程式設計、電腦視覺、UI 自動化等技術。請勿將其用於任何營利性或商業用途。
- 使用本軟體可能會導致帳號被封。請在了解風險後再使用。
'''

        readme_path = os.path.join(package_dir, "README.txt")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        self.log("✅ 創建README.txt")

        # =============================================================================
        # 📦 最終安裝包內容規範 (IMPORTANT - DO NOT MODIFY)
        # =============================================================================
        # 壓縮檔打包完成後應該只包含以下文件，請勿添加或刪除任何文件：
        #
        # ✅ 必須包含的文件:
        #   • auto_click.exe              (AutoHotkey自動點擊工具)
        #   • GameTools_HealthMonitor.exe (主程式可執行文件)
        #   • language_packs.json         (語言包配置)
        #   • README.txt                  (使用說明)
        #   • 使用說明.md                 (詳細說明文檔)
        #   • 啟動工具.bat               (啟動腳本)
        #
        # ❌ 禁止包含的文件:
        #   • screenshots/                (動態生成，不應預打包)
        #   • health_monitor_config.json  (用戶配置，不應預打包)
        #   • 任何其他臨時或測試文件
        #
        # 修改此邏輯前請仔細評估影響！
        # =============================================================================

        # 創建 ZIP
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        zip_name = f"GameTools_HealthMonitor_v{APP_VERSION}_{timestamp}"
        zip_path = os.path.join(self.dist_dir, zip_name)

        shutil.make_archive(zip_path, 'zip', package_dir)
        self.log(f"✅ 創建安裝包: {zip_name}.zip")

        return True

    def build_all(self):
        """執行完整構建"""
        self.log("🚀 開始構建 Sid輔助工具 - 完整修復版本")

        try:
            steps = [
                ("依賴檢查", self.check_dependencies),
                ("主工具", self.build_main_tool),
                ("安裝包", self.create_installation_package)
            ]

            for step_name, step_func in steps:
                self.start_step(step_name)
                if not step_func():
                    self.log(f"❌ 構建失敗於: {step_name}")
                    return False
                self.end_step(step_name)

            total_time = datetime.now() - self.start_time
            minutes = total_time.total_seconds() / 60
            self.log(f"🎯 總耗時: {minutes:.1f} 分鐘")
            self.log("🎉 構建成功完成！")
            self.log("📦 安裝包位於 dist/ 目錄")

            return True

        except Exception as e:
            self.log(f"❌ 構建異常: {e}")
            return False

def main():
    builder = GameToolBuilder()
    success = builder.build_all()
    input("\n按任意鍵結束...")
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())

    def show_build_estimate(self):
        """顯示構建時間預估"""
        self.log("📊 構建時間預估:")
        self.log("  • 依賴檢查: < 1 分鐘")
        self.log("  • 主工具打包: 8-15 分鐘 (PyInstaller 處理時間)")
        self.log("  • 安裝包創建: < 1 分鐘")
        self.log("  • 總計預估: 9-17 分鐘")
        self.log("💡 提示: PyInstaller 打包速度取決於代碼複雜度和依賴數量")

    def show_total_time(self):
        """顯示總構建時間"""
        total_duration = datetime.now() - self.start_time
        minutes = total_duration.total_seconds() / 60
        self.log(f"🎯 總構建耗時: {minutes:.1f} 分鐘")

    def check_dependencies(self):
        """檢查必要的依賴"""
        self.log("檢查依賴...")
        
        required_packages = [
            "PyInstaller"
        ]
        
        missing_required = []
        
        for package in required_packages:
            try:
                # 特殊處理一些模組名稱
                if package == "PyInstaller":
                    __import__("PyInstaller")
                else:
                    __import__(package.lower().replace("-", "_"))
                self.log(f"✅ {package} 已安裝")
            except ImportError:
                missing_required.append(package)
                self.log(f"❌ {package} 未安裝")
        
        if missing_required:
            self.log(f"❌ 缺少必要的依賴: {', '.join(missing_required)}")
            self.log("請運行以下命令安裝:")
            for package in missing_required:
                self.log(f"  pip install {package}")
            return False
        
        self.log("✅ 所有必要依賴已滿足")
        return True

    def build_main_tool(self):
        """構建主工具"""
        source_file = os.path.join(self.src_dir, "health_monitor.py")
        if not os.path.exists(source_file):
            self.log("❌ health_monitor.py 不存在")
            return False
        
        # 創建安裝包目錄
        package_dir = os.path.join(self.dist_dir, "GameTools_Package")
        os.makedirs(package_dir, exist_ok=True)
        
        try:
            # 使用 spec 檔案進行構建（更穩定）
            spec_file = os.path.join(self.project_dir, "GameTools_HealthMonitor.spec")
            if os.path.exists(spec_file):
                self.log("使用現有的 spec 檔案進行構建...")
                cmd = [
                    "C:/Users/user/AppData/Local/Microsoft/WindowsApps/python3.10.exe", "-m", "PyInstaller",
                    spec_file
                ]
            else:
                self.log("spec 檔案不存在，使用命令行參數...")
                # 構建命令基本參數
                cmd = [
                    "C:/Users/user/AppData/Local/Microsoft/WindowsApps/python3.10.exe", "-m", "PyInstaller",
                    "--onefile",
                    "--noconsole",  # 隱藏命令視窗，只顯示GUI
                    "--clean",
                    "--name", "GameTools_HealthMonitor",
                    "--icon", self.icon_file,
                    # OpenCV 相關參數
                    "--hidden-import", "cv2",
                    "--collect-data", "cv2",
                    # NumPy 相關參數
                    "--hidden-import", "numpy",
                    # Pillow 相關參數
                    "--hidden-import", "PIL",
                    "--hidden-import", "PIL.Image",
                    "--hidden-import", "PIL.ImageTk",
                    "--hidden-import", "PIL.ImageDraw",
                    "--hidden-import", "PIL._imaging",
                    "--copy-metadata", "Pillow",
                    "--collect-data", "PIL",
                    # 其他必要依賴
                    "--hidden-import", "mss",
                    "--hidden-import", "keyboard",
                    "--hidden-import", "pygetwindow",
                    "--hidden-import", "pyautogui",
                    "--hidden-import", "psutil",
                    "--hidden-import", "tkinter",
                    "--hidden-import", "tkinter.ttk",
                    "--hidden-import", "tkinter.messagebox",
                    "--hidden-import", "_tkinter",
                    "--collect-data", "tkinter",
                    # 添加數據文件
                    "--add-data", f"{os.path.join(self.project_dir, 'scripts', 'auto_click.ahk')};.",
                    "--add-data", f"{os.path.join(self.src_dir, 'auto_click.exe')};.",
                    "--add-data", f"{os.path.join(self.src_dir, 'language_packs.json')};.",
                    source_file
                ]
            # 自動添加 tcl/tk DLL 與 tcl 資料，避免 _tkinter 在打包後找不到依賴
            try:
                python_home = os.path.normpath(sys.exec_prefix)
            except Exception:
                python_home = None

            if python_home and not os.path.exists(spec_file):
                dlls_dir = os.path.join(python_home, 'DLLs')
                tcl86 = os.path.join(dlls_dir, 'tcl86t.dll')
                tk86 = os.path.join(dlls_dir, 'tk86t.dll')
                tk_pyd = os.path.join(dlls_dir, '_tkinter.pyd')
                # 加入 DLL（作為二進位資源）
                if os.path.exists(tcl86):
                    cmd += ["--add-binary", f"{tcl86};."]
                if os.path.exists(tk86):
                    cmd += ["--add-binary", f"{tk86};."]
                if os.path.exists(tk_pyd):
                    cmd += ["--add-binary", f"{tk_pyd};."]

                # 加入 tcl 資料夾（PyInstaller 需要 tcl 路徑以支援 tkinter）
                tcl_base = os.path.join(python_home, 'tcl')
                if os.path.exists(tcl_base):
                    # 把整個 tcl 目錄打包到執行檔旁的 tcl 子資料夾
                    cmd += ["--add-data", f"{tcl_base};tcl"]

                # 加入 Pillow 的 C 擴展模組（.pyd 檔案），避免 _imaging 等模組找不到
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
                            cmd += ["--add-binary", f"{pyd_path};PIL"]
                except Exception as e:
                    self.log(f"⚠️ 加入 Pillow .pyd 檔案時發生錯誤: {e}")

                # 嘗試使用 Pillow 的 hook（如果可用）
                try:
                    import PyInstaller.hooks
                    hook_path = os.path.join(os.path.dirname(PyInstaller.hooks.__file__), 'hook-PIL.py')
                    if os.path.exists(hook_path):
                        cmd += ["--additional-hooks-dir", os.path.dirname(hook_path)]
                        self.log("✅ 使用 Pillow hook")
                    else:
                        self.log("⚠️ Pillow hook 不存在")
                except Exception as e:
                    self.log(f"⚠️ 載入 Pillow hook 時發生錯誤: {e}")

                # 額外確保 Pillow 的核心模組被包含
                cmd += ["--hidden-import", "PIL._imaging"]
                cmd += ["--collect-binaries", "PIL"]

            self.log(f"執行命令: {' '.join(cmd)}")
            self.log(f"工作目錄: {self.project_dir}")

            # 為避免 subprocess 在解碼非 utf-8 bytes 時拋出 UnicodeDecodeError，先以 bytes 模式抓取輸出，
            # 再以 errors='replace' 解碼以便安全地記錄錯誤資訊。
            result = subprocess.run(
                cmd,
                cwd=self.project_dir,
                capture_output=True
            )
            stdout = result.stdout.decode('utf-8', errors='replace') if result.stdout else ''
            stderr = result.stderr.decode('utf-8', errors='replace') if result.stderr else ''
            
            if result.returncode != 0:
                self.log(f"❌ PyInstaller 執行失敗:")
                self.log(f"錯誤輸出: {stderr}")
                self.log(f"標準輸出: {stdout}")
                return False
            
            # 找出 PyInstaller 可能生成的 exe 路徑並移動到 package 目錄
            possible_sources = [
                os.path.join(self.dist_dir, "GameTools_HealthMonitor.exe"),
                os.path.join(self.dist_dir, "GameTools_HealthMonitor", "GameTools_HealthMonitor.exe")
            ]

            found_source = None
            for p in possible_sources:
                if os.path.exists(p):
                    found_source = p
                    break

            if not found_source:
                # 仍嘗試檢查 dist/GameTools_Package（舊流程或已被其他步驟移動）
                alt = os.path.join(package_dir, "GameTools_HealthMonitor.exe")
                if os.path.exists(alt):
                    self.log(f"⚠️ 可用的 exe 已存在於 package 目錄: {alt}")
                    return True

                self.log("❌ 找不到生成的exe文件")
                return False

            target_exe = os.path.join(package_dir, "GameTools_HealthMonitor.exe")
            if os.path.exists(target_exe):
                os.remove(target_exe)
            shutil.move(found_source, target_exe)
            self.log(f"✅ 主工具打包完成: {target_exe}")

            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"❌ PyInstaller 執行失敗: {e}")
            return False
        except Exception as e:
            self.log(f"❌ 構建主工具時發生錯誤: {e}")
            return False

    def create_installation_package(self):
        """創建安裝包 - 包含所有必要文件"""
        package_dir = os.path.join(self.dist_dir, "GameTools_Package")
        
        # 確保目錄存在
        os.makedirs(package_dir, exist_ok=True)
        
        # 複製所有必要文件到安裝包目錄
        files_to_copy = [
            # 主程式文件
            ("dist/GameTools_Package/GameTools_HealthMonitor.exe", "GameTools_HealthMonitor.exe"),
            ("src for DEVELOPER/auto_click.exe", "auto_click.exe"),
            
            # 語言包文件（用戶界面所需）
            ("src for DEVELOPER/language_packs.json", "language_packs.json"),
            
            # 文檔文件
            ("src for DEVELOPER/使用說明.md", "使用說明.md"),
            ("github/README.md", "README.md"),
        ]
        
        for src_path, dst_name in files_to_copy:
            src_full_path = os.path.join(self.project_dir, src_path)
            dst_full_path = os.path.join(package_dir, dst_name)
            
            if os.path.exists(src_full_path):
                # 確保目標目錄存在
                os.makedirs(os.path.dirname(dst_full_path), exist_ok=True)
                shutil.copy2(src_full_path, dst_full_path)
                self.log(f"✅ 複製文件: {dst_name}")
            else:
                self.log(f"⚠️ 文件不存在，跳過: {src_path}")
        
        # 注意：health_monitor_config.json 和 screenshots 文件夹
        # 應該由用戶在使用過程中自行創建，不應預先包含在安裝包中
        # screenshots 目錄會在使用工具框選截圖時自動生成
        
        # 創建啟動工具.bat
        startup_bat_content = '''@echo off
chcp 65001 >nul
echo 正在啟動 PathofExile Sid Sid輔助工具...
echo.
echo 請以管理員權限運行此工具以獲得最佳體驗
echo.
start "" "GameTools_HealthMonitor.exe"
'''
        
        startup_bat_path = os.path.join(package_dir, "啟動工具.bat")
        with open(startup_bat_path, 'w', encoding='utf-8') as f:
            f.write(startup_bat_content)
        
        self.log("✅ 創建啟動工具.bat")

        # 創建README文件
        readme_content = '''# Sid輔助工具

## 使用說明
1. 直接運行 GameTools_HealthMonitor.exe 即可開始使用
2. 無需額外安裝任何依賴，所有必要組件已內嵌
3. 首次使用建議閱讀使用說明.md了解各項功能

## 功能說明
- 血魔監控：智能監控血量魔力並自動使用藥水
- 快捷操作：F3清包、F5回城、F6取物等快捷功能
- 自動化操作：支持各種遊戲內自動化操作
- 完全免費開放，無任何使用限制

## 技術支持
本工具完全開源，源代碼可在專案庫中查看。
如有問題，請參考使用說明.md或查看源代碼。

## 版本資訊
- 版本：v1.0.6 
- 構建時間：''' + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + '''
- 版本類型：無功能限制

## 重要聲明
- 本軟體是免費開源的。如果你被收費,請立即退款。請造訪 GitHub 下載最新的官方版本。
- 本軟體僅供個人使用,用於學習Python 程式設計、電腦視覺、UI 自動化等技術。請勿將其用於任何營利性或商業用途。
- 使用本軟體可能會導致帳號被封。請在了解風險後再使用。
'''
        
        readme_path = os.path.join(package_dir, "README.txt")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        self.log("✅ 創建README文件")

        # =============================================================================
        # 📦 最終安裝包內容規範 (IMPORTANT - DO NOT MODIFY)
        # =============================================================================
        # 壓縮檔打包完成後應該只包含以下文件，請勿添加或刪除任何文件：
        #
        # ✅ 必須包含的文件:
        #   • auto_click.exe              (AutoHotkey自動點擊工具)
        #   • GameTools_HealthMonitor.exe (主程式可執行文件)
        #   • language_packs.json         (語言包配置)
        #   • README.txt                  (使用說明)
        #   • 使用說明.md                 (詳細說明文檔)
        #   • 啟動工具.bat               (啟動腳本)
        #
        # ❌ 禁止包含的文件:
        #   • screenshots/                (動態生成，不應預打包)
        #   • health_monitor_config.json  (用戶配置，不應預打包)
        #   • 任何其他臨時或測試文件
        #
        # 修改此邏輯前請仔細評估影響！
        # =============================================================================
        
        # 創建ZIP包
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            zip_name = f"GameTools_HealthMonitor_v1.0.6_{timestamp}"
            zip_path = os.path.join(self.dist_dir, zip_name)
            
            shutil.make_archive(zip_path, 'zip', package_dir)
            
            self.log(f"✅ 創建安裝包: {zip_name}.zip")
            return True
            
        except Exception as e:
            self.log(f"❌ 創建安裝包失敗: {e}")
            return False

    def build_all(self):
        """執行完整構建"""
        self.log("🚀 開始構建 Sid輔助工具 - 開源版本")
        self.show_build_estimate()
        
        try:
            # 執行構建步驟（開源版本，移除授權相關步驟）
            build_steps = [
                ("依賴檢查", self.check_dependencies),
                ("主工具", self.build_main_tool),
                ("安裝包", self.create_installation_package)
            ]
            
            for step_name, step_func in build_steps:
                self.start_step(step_name)
                success = step_func()
                self.end_step(step_name)
                
                if not success:
                    self.log(f"❌ 構建失敗於步驟: {step_name}")
                    return False
                    
                print()  # 添加空行分隔
            
            self.show_total_time()
            self.log("🎉 構建成功完成！")
            self.log("📦 安裝包位於 dist/ 目錄")
            
            return True
            
        except Exception as e:
            self.log(f"❌ 構建過程中發生錯誤: {e}")
            return False

def main():
    """主函數"""
    builder = GameToolBuilder()
    success = builder.build_all()
    
    # 等待用戶按鍵
    input("\\n按任意鍵結束...")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())