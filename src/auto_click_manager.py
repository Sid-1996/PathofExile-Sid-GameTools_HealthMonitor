import os
import sys
import threading
import subprocess
import time
import psutil
import pyautogui
from utils import get_app_dir


class AutoClickManager:
    def __init__(self, app):
        self._app = app
        self.auto_click_process = None
        self.auto_click_script_path = os.path.join(get_app_dir(), "auto_click.ahk")
        self.auto_click_exe_path = os.path.join(get_app_dir(), "auto_click.exe")
        self.auto_click_active = False
        self.auto_click_running = False
        self.auto_click_thread = None

    def setup_auto_click_listener(self):
        """設定自動點擊功能 - 自動啟動AHK腳本"""
        try:
            print("設定自動點擊功能...")
            self.start_auto_click_ahk()
        except Exception as e:
            print(f"設定自動點擊功能失敗: {e}")

    def start_auto_click_ahk(self):
        """啟動AHK自動點擊腳本 - 支援EXE版本優先"""
        try:
            if self.auto_click_process:
                if isinstance(self.auto_click_process, psutil.Process):
                    if self.auto_click_process.is_running():
                        print("AHK自動點擊已經在運行中")
                        return
                elif self.auto_click_process.poll() is None:
                    print("AHK自動點擊已經在運行中")
                    return

            if getattr(sys, 'frozen', False):
                process_name = "GameTools_HealthMonitor.exe"
            else:
                actual_executable = os.path.basename(sys.executable)
                print(f"實際Python可執行文件: {actual_executable}")
                print(f"完整路徑: {sys.executable}")

                current_pid = os.getpid()
                current_process = psutil.Process(current_pid)
                actual_process_name = current_process.name()
                print(f"當前進程PID: {current_pid}")
                print(f"當前進程名稱: {actual_process_name}")

                process_name = actual_process_name

            print(f"將傳遞給AHK的進程名稱: {process_name}")

            if os.path.exists(self.auto_click_exe_path):
                print(f"找到EXE版本: {self.auto_click_exe_path}")
                try:
                    self.auto_click_process = subprocess.Popen([
                        self.auto_click_exe_path,
                        process_name
                    ], creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(0.3)
                    if self.auto_click_process.poll() is not None:
                        msg = ("auto_click.exe 啟動後異常終止，請檢查檔案是否完整\n"
                               "auto_click.exe exited unexpectedly. The file may be corrupted.")
                        print(msg)
                        self._app.status_tab.add_status_message(msg, "error")
                    else:
                        print(" AHK自動點擊(EXE版)已啟動")
                        print(" 現在可以直接使用 CTRL+左鍵 進行自動連點")
                        print(" 當主程式退出時，AHK腳本會自動關閉")
                        self._app.status_tab.add_status_message(
                            "CTRL+Click 自動連點已啟動 (auto_click.exe)",
                            "success"
                        )
                except Exception as e:
                    msg = f"啟動 auto_click.exe 失敗: {e}\nFailed to start auto_click.exe: {e}"
                    print(msg)
                    self._app.status_tab.add_status_message(msg, "error")
                return

            elif os.path.exists(self.auto_click_script_path):
                print(f"找到AHK腳本: {self.auto_click_script_path}")

                ahk_paths = [
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey32.exe",
                    r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
                    r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe"
                ]

                ahk_exe = None
                for path in ahk_paths:
                    if os.path.exists(path):
                        ahk_exe = path
                        break

                if not ahk_exe:
                    msg = ("[ERROR] 未找到AutoHotkey程式，請確保已安裝AutoHotkey或使用EXE版本\n"
                           "AutoHotkey not found. Please install AutoHotkey v2 or use the EXE version.")
                    print(msg)
                    self._app.status_tab.add_status_message(msg, "error")
                    return

                self.auto_click_process = subprocess.Popen([
                    ahk_exe,
                    self.auto_click_script_path,
                    process_name
                ], creationflags=subprocess.CREATE_NO_WINDOW)

                print(" AHK自動點擊已啟動")
                print(" 現在可以直接使用 CTRL+左鍵 進行自動連點")
                print(" 當主程式退出時，AHK腳本會自動關閉")

            else:
                msg = ("[ERROR] 未找到AHK腳本或EXE文件\n"
                       "請確保存在以下文件之一：\n"
                       f"  - {self.auto_click_exe_path}\n"
                       f"  - {self.auto_click_script_path}\n"
                       "Auto-click files not found. Please reinstall the package or restore the missing files.")
                print(msg)
                self._app.status_tab.add_status_message(msg, "error")

        except Exception as e:
            msg = f"[ERROR] 啟動AHK自動點擊失敗: {e}\nAuto-click startup failed: {e}"
            print(msg)
            self._app.status_tab.add_status_message(msg, "error")

    def stop_auto_click_ahk(self):
        """停止AHK自動點擊腳本"""
        try:
            if self.auto_click_process is None:
                print("AHK自動點擊未運行")
                return

            if isinstance(self.auto_click_process, psutil.Process):
                if self.auto_click_process.is_running():
                    self.auto_click_process.terminate()
                    self.auto_click_process.wait(timeout=3)
                    print("[STOP] AHK自動點擊已停止")
                else:
                    print("AHK自動點擊未運行")
            else:
                if self.auto_click_process.poll() is None:
                    self.auto_click_process.terminate()
                    self.auto_click_process.wait(timeout=3)
                    print("[STOP] AHK自動點擊已停止")
                else:
                    print("AHK自動點擊未運行")
        except psutil.NoSuchProcess:
            print("[STOP] AHK自動點擊進程已不存在")
        except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
            if isinstance(self.auto_click_process, psutil.Process):
                self.auto_click_process.kill()
            else:
                self.auto_click_process.kill()
            print("[STOP] AHK自動點擊已強制停止")
        except Exception as e:
            print(f"停止AHK自動點擊時發生錯誤: {e}")
        finally:
            self.auto_click_process = None

    def toggle_auto_click(self):
        """切換自動點擊狀態（備用方案）"""
        if self.auto_click_active:
            self.stop_auto_click()
            print("[STOP] 自動點擊已停止（Ctrl+Shift+Z）")
        else:
            self.start_auto_click()
            print(" 自動點擊已啟動（Ctrl+Shift+Z再次按下可停止）")

    def start_auto_click(self):
        """開始自動點擊"""
        if not self.auto_click_active:
            print("啟動自動點擊...")
            self.auto_click_active = True
            self.auto_click_running = True
            self.auto_click_thread = threading.Thread(target=self.auto_click_loop, daemon=True)
            self.auto_click_thread.start()
            print("自動點擊執行緒已啟動")
        else:
            print("自動點擊已經在運行中")

    def stop_auto_click(self):
        """停止自動點擊"""
        if self.auto_click_active:
            print("停止自動點擊...")
            self.auto_click_active = False
            self.auto_click_running = False
            print("自動點擊已停止")
        else:
            print("自動點擊已經是停止狀態")
        self.auto_click_running = False

    def auto_click_loop(self):
        """自動點擊循環 - 模擬AHK的while循環行為"""
        print("進入自動點擊循環")
        click_count = 0

        while self.auto_click_running and self.auto_click_active:
            try:
                if not (self._app.ctrl_pressed and self._app.left_button_pressed):
                    print("按鍵狀態改變，結束自動點擊循環")
                    break

                current_x, current_y = pyautogui.position()
                pyautogui.leftClick(current_x, current_y)
                click_count += 1

                if click_count % 20 == 0:
                    print(f"已點擊 {click_count} 次，位置: ({current_x}, {current_y})")

                time.sleep(self._app.click_interval)

            except Exception as e:
                print(f"自動點擊錯誤: {e}")
                break

        print(f"自動點擊循環結束，總共點擊 {click_count} 次")
        self.auto_click_active = False
        self.auto_click_running = False
