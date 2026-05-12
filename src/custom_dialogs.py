"""
自訂對話框模組
提供動態尺寸調整的本地化對話框，支援長文本顯示
"""

import tkinter as tk
from tkinter import ttk, font as tkfont
import ctypes


# Windows API 函數用於更好的窗口管理
user32 = ctypes.windll.user32
GetWindowTextW = ctypes.windll.user32.GetWindowTextW
GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
SendMessageW = ctypes.windll.user32.SendMessageW

GetWindowTextW.argtypes = [ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_int]
GetWindowTextW.restype = ctypes.c_int
SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_long]
SendMessageW.restype = ctypes.c_long


class CustomMessageBox:
    """自訂對話框類，支援動態尺寸調整和本地化文本"""
    
    result = None
    
    # 對話框尺寸限制
    MIN_WIDTH = 420
    MAX_WIDTH = 760
    MIN_HEIGHT = 180
    MAX_HEIGHT = 560
    MESSAGE_WRAP = 520

    @staticmethod
    def _resolve_parent(parent=None):
        """解析父窗口，確保窗口存在且可見"""
        candidate = parent or tk._default_root
        if candidate is None:
            return None

        try:
            if not candidate.winfo_exists():
                return None
            if candidate.state() == 'withdrawn':
                return None
        except Exception:
            return None

        return candidate

    @staticmethod
    def _build_dialog(title, message, buttons, parent=None, accent=None, close_result=False):
        """構建對話框"""
        CustomMessageBox.result = None
        parent = CustomMessageBox._resolve_parent(parent)

        window = tk.Toplevel(parent)
        window.title(title or 'Message')
        window.resizable(False, False)
        window.minsize(CustomMessageBox.MIN_WIDTH, CustomMessageBox.MIN_HEIGHT)

        if parent is not None:
            window.transient(parent)
        window.grab_set()

        container = ttk.Frame(window, padding=(20, 18, 20, 14))
        container.pack(fill=tk.BOTH, expand=True)

        message_font = tkfont.nametofont('TkDefaultFont')
        message_widget = tk.Message(
            container,
            text=message or '',
            width=CustomMessageBox.MESSAGE_WRAP,
            justify=tk.LEFT,
            anchor='w',
            font=message_font,
            foreground=accent or 'black',
            padx=0,
            pady=0,
        )
        message_widget.pack(fill=tk.BOTH, expand=True)

        button_frame = ttk.Frame(container)
        button_frame.pack(fill=tk.X, pady=(18, 0))

        focus_button = None
        for button in reversed(buttons):
            btn = ttk.Button(
                button_frame,
                text=button['text'],
                command=lambda value=button['result']: CustomMessageBox._close(window, value),
                width=max(12, len(button['text']) + 2),
            )
            btn.pack(side=tk.RIGHT, padx=(8, 0))
            if button.get('default') and focus_button is None:
                focus_button = btn

        if focus_button is not None:
            focus_button.focus_set()

        default_result = next((button['result'] for button in buttons if button.get('default')), True)
        window.bind('<Return>', lambda e: CustomMessageBox._close(window, default_result))
        window.bind('<Escape>', lambda e: CustomMessageBox._close(window, close_result))
        window.protocol('WM_DELETE_WINDOW', lambda: CustomMessageBox._close(window, close_result))

        window.update_idletasks()

        width = min(max(container.winfo_reqwidth() + 8, CustomMessageBox.MIN_WIDTH), CustomMessageBox.MAX_WIDTH)
        if width != CustomMessageBox.MIN_WIDTH:
            message_widget.configure(width=max(320, width - 70))
            window.update_idletasks()

        height = min(max(container.winfo_reqheight() + 8, CustomMessageBox.MIN_HEIGHT), CustomMessageBox.MAX_HEIGHT)

        if parent is not None and parent.winfo_exists():
            parent.update_idletasks()
            parent_x = parent.winfo_rootx()
            parent_y = parent.winfo_rooty()
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
            x = parent_x + max(0, (parent_width - width) // 2)
            y = parent_y + max(0, (parent_height - height) // 2)
        else:
            screen_width = window.winfo_screenwidth()
            screen_height = window.winfo_screenheight()
            x = max(0, (screen_width - width) // 2)
            y = max(0, (screen_height - height) // 2)

        window.geometry(f'{width}x{height}+{x}+{y}')
        window.wait_window()
        return CustomMessageBox.result

    @staticmethod
    def show_info(title, message, parent=None):
        """顯示信息對話框"""
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            close_result=True,
        )
        return True

    @staticmethod
    def show_warning(title, message, parent=None):
        """顯示警告對話框"""
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            accent='#8a6d00',
            close_result=True,
        )
        return True

    @staticmethod
    def show_error(title, message, parent=None):
        """顯示錯誤對話框"""
        CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[{'text': 'OK (Enter)', 'result': True, 'default': True}],
            parent=parent,
            accent='#b00020',
            close_result=True,
        )
        return True

    @staticmethod
    def ask_yes_no(title, message, parent=None):
        """顯示是/否確認對話框"""
        return CustomMessageBox._build_dialog(
            title,
            message,
            buttons=[
                {'text': 'No (Esc)', 'result': False},
                {'text': 'Yes (Enter)', 'result': True, 'default': True},
            ],
            parent=parent,
            close_result=False,
        )

    @staticmethod
    def _close(window, result):
        """關閉對話框並返回結果"""
        CustomMessageBox.result = result
        window.destroy()


def setup_custom_messagebox():
    """設置自訂對話框為預設 messagebox"""
    from tkinter import messagebox
    
    def _custom_messagebox_info(title=None, message=None, **options):
        return CustomMessageBox.show_info(title or 'Info', message or '', parent=options.get('parent'))

    def _custom_messagebox_warning(title=None, message=None, **options):
        return CustomMessageBox.show_warning(title or 'Warning', message or '', parent=options.get('parent'))

    def _custom_messagebox_error(title=None, message=None, **options):
        return CustomMessageBox.show_error(title or 'Error', message or '', parent=options.get('parent'))

    def _custom_messagebox_askyesno(title=None, message=None, **options):
        return CustomMessageBox.ask_yes_no(title or 'Confirm', message or '', parent=options.get('parent'))

    # 替換預設 messagebox 函數
    messagebox.showinfo = _custom_messagebox_info
    messagebox.showwarning = _custom_messagebox_warning
    messagebox.showerror = _custom_messagebox_error
    messagebox.askyesno = _custom_messagebox_askyesno
