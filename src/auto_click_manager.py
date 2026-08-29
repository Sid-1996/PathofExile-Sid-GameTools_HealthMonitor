import logging
import os
import sys
import threading
import subprocess
import time
import psutil
import pyautogui
from utils import get_app_dir

logger = logging.getLogger(__name__)


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
            logger.info("設定自動點擊功能...")
            self.start_auto_click_ahk()
        except Exception as e:
            logger.error("設定自動點擊功能失敗: %s", e)

    def start_auto_click_ahk(self):
        """啟動AHK自動點擊腳本 - 支援EXE版本優先"""
        try:
            if self.auto_click_process:
                if isinstance(self.auto_click_process, psutil.Process):
                    if self.auto_click_process.is_running():
                        logger.info("AHK自動點擊已經在運行中")
                        return
                elif self.auto_click_process.poll() is None:
                    logger.info("AHK自動點擊已經在運行中")
                    return

            if getattr(sys, "frozen", False):
                process_name = "GameTools_HealthMonitor.exe"
            else:
                actual_executable = os.path.basename(sys.executable)
                logger.debug("實際Python可執行文件: %s", actual_executable)
                logger.debug("完整路徑: %s", sys.executable)

                current_pid = os.getpid()
                current_process = psutil.Process(current_pid)
                actual_process_name = current_process.name()
                logger.debug("當前進程PID: %s", current_pid)
                logger.debug("當前進程名稱: %s", actual_process_name)

                process_name = actual_process_name

            logger.debug("將傳遞給AHK的進程名稱: %s", process_name)

            if os.path.exists(self.auto_click_exe_path):
                logger.debug("找到EXE版本: %s", self.auto_click_exe_path)
                try:
                    self.auto_click_process = subprocess.Popen([self.auto_click_exe_path, process_name], creationflags=subprocess.CREATE_NO_WINDOW)
                    time.sleep(0.3)
                    if self.auto_click_process.poll() is not None:
                        msg = self._app.get_text("auto_click_exe_crashed")
                        logger.error("%s", msg)
                        self._app.status_tab.add_status_message(msg, "error")
                        self._app.show_floating_notice(msg, "error")
                    else:
                        logger.info("AHK自動點擊(EXE版)已啟動")
                        logger.info("現在可以直接使用 CTRL+左鍵 進行自動連點")
                        logger.info("當主程式退出時，AHK腳本會自動關閉")
                        self._app.status_tab.add_status_message(self._app.get_text("auto_click_started"), "success")
                        self._app.set_ahk_click_status(True)
                except Exception as e:
                    msg = self._app.get_text("auto_click_start_failed").format(error=e)
                    logger.error("%s", msg)
                    self._app.status_tab.add_status_message(msg, "error")
                    self._app.show_floating_notice(msg, "error")
                return

            elif os.path.exists(self.auto_click_script_path):
                logger.debug("找到AHK腳本: %s", self.auto_click_script_path)

                ahk_paths = [
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
                    r"C:\Program Files\AutoHotkey\v2\AutoHotkey32.exe",
                    r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
                    r"C:\Program Files (x86)\AutoHotkey\AutoHotkey.exe",
                ]

                ahk_exe = None
                for path in ahk_paths:
                    if os.path.exists(path):
                        ahk_exe = path
                        break

                if not ahk_exe:
                    msg = self._app.get_text("auto_click_ahk_not_found")
                    logger.error("%s", msg)
                    self._app.status_tab.add_status_message(msg, "error")
                    self._app.show_floating_notice(msg, "error")
                    return

                self.auto_click_process = subprocess.Popen([ahk_exe, self.auto_click_script_path, process_name], creationflags=subprocess.CREATE_NO_WINDOW)

                logger.info("AHK自動點擊已啟動")
                logger.info("現在可以直接使用 CTRL+左鍵 進行自動連點")
                logger.info("當主程式退出時，AHK腳本會自動關閉")
                self._app.status_tab.add_status_message(self._app.get_text("auto_click_started"), "success")
                self._app.set_ahk_click_status(True)

            else:
                msg = self._app.get_text("auto_click_files_missing").format(exe_path=self.auto_click_exe_path, script_path=self.auto_click_script_path)
                logger.error("%s", msg)
                self._app.status_tab.add_status_message(msg, "error")
                self._app.show_floating_notice(msg, "error")

        except Exception as e:
            msg = self._app.get_text("auto_click_ahk_start_failed").format(error=e)
            logger.error("%s", msg)
            self._app.status_tab.add_status_message(msg, "error")
            self._app.show_floating_notice(msg, "error")

    def stop_auto_click_ahk(self):
        """停止AHK自動點擊腳本"""
        try:
            if self.auto_click_process is None:
                logger.info("AHK自動點擊未運行")
                return

            if isinstance(self.auto_click_process, psutil.Process):
                if self.auto_click_process.is_running():
                    self.auto_click_process.terminate()
                    self.auto_click_process.wait(timeout=3)
                    logger.info("AHK自動點擊已停止")
                else:
                    logger.info("AHK自動點擊未運行")
            else:
                if self.auto_click_process.poll() is None:
                    self.auto_click_process.terminate()
                    self.auto_click_process.wait(timeout=3)
                    logger.info("AHK自動點擊已停止")
                else:
                    logger.info("AHK自動點擊未運行")
        except psutil.NoSuchProcess:
            logger.info("AHK自動點擊進程已不存在")
        except (subprocess.TimeoutExpired, psutil.TimeoutExpired):
            if isinstance(self.auto_click_process, psutil.Process):
                self.auto_click_process.kill()
            elif self.auto_click_process is not None:
                self.auto_click_process.kill()
            logger.warning("AHK自動點擊已強制停止")
        except Exception as e:
            logger.error("停止AHK自動點擊時發生錯誤: %s", e)
        finally:
            self.auto_click_process = None
            try:
                self._app.set_ahk_click_status(False)
            except Exception:
                pass

    def toggle_auto_click(self):
        """切換自動點擊狀態（備用方案）"""
        if self.auto_click_active:
            self.stop_auto_click()
            logger.info("自動點擊已停止（Ctrl+Shift+Z）")
        else:
            self.start_auto_click()
            logger.info("自動點擊已啟動（Ctrl+Shift+Z再次按下可停止）")

    def start_auto_click(self):
        """開始自動點擊"""
        if not self.auto_click_active:
            logger.info("啟動自動點擊...")
            self.auto_click_active = True
            self.auto_click_running = True
            self.auto_click_thread = threading.Thread(target=self.auto_click_loop, daemon=True)
            self.auto_click_thread.start()
            logger.info("自動點擊執行緒已啟動")
        else:
            logger.info("自動點擊已經在運行中")

    def stop_auto_click(self):
        """停止自動點擊"""
        if self.auto_click_active:
            logger.info("停止自動點擊...")
            self.auto_click_active = False
            self.auto_click_running = False
            logger.info("自動點擊已停止")
        else:
            logger.info("自動點擊已經是停止狀態")
        self.auto_click_running = False

    def auto_click_loop(self):
        """自動點擊循環 - 模擬AHK的while循環行為"""
        logger.info("進入自動點擊循環")
        click_count = 0

        while self.auto_click_running and self.auto_click_active:
            try:
                if not (self._app.ctrl_pressed and self._app.left_button_pressed):
                    logger.info("按鍵狀態改變，結束自動點擊循環")
                    break

                current_x, current_y = pyautogui.position()
                pyautogui.leftClick(current_x, current_y)
                click_count += 1

                if click_count % 20 == 0:
                    logger.debug("已點擊 %s 次，位置: (%s, %s)", click_count, current_x, current_y)

                time.sleep(self._app.click_interval)

            except Exception as e:
                logger.error("自動點擊錯誤: %s", e)
                break

        logger.info("自動點擊循環結束，總共點擊 %s 次", click_count)
        self.auto_click_active = False
        self.auto_click_running = False
