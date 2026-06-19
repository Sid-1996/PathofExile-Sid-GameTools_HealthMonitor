import threading
import time
from typing import Any, Optional


class AppState:
    """Shared application state context.

    Holds cross-cutting state (monitoring, combo, pause flags)
    and provides thread-safe access via locks.

    Usage: self.state = AppState(self) early in app.__init__.
    Access shared state via self.state.xxx.
    """

    # Type annotations so pyright can trace attributes
    _is_closing: bool
    monitoring: bool
    monitor_thread: Optional[threading.Thread]
    monitor_interval: float
    monitoring_lock: threading.RLock
    combo_sets: list
    combo_enabled: list
    combo_thread: Optional[threading.Thread]
    combo_running: bool
    combo_hotkeys: dict
    combo_lock: threading.RLock
    global_pause: bool
    monitoring_was_active: bool
    combo_was_running: bool
    global_pause_lock: threading.RLock
    last_trigger_times: dict
    inventory_clear_interrupt: bool
    gui_minimized_for_clear: bool
    original_gui_geometry: Optional[str]
    original_gui_state: Optional[str]
    gui_was_foreground_before_minimize: bool

    def __init__(self, app: Any) -> None:
        self._app = app
        self.root = app.root

        # Closing guard
        self._is_closing = False

        # Monitoring state
        self.monitoring = False
        self.monitor_thread = None
        self.monitor_interval = 0.1
        self.monitoring_lock = threading.RLock()

        # Combo state
        self.combo_sets = []
        self.combo_enabled = [False, False, False]
        self.combo_thread = None
        self.combo_running = False
        self.combo_hotkeys = {}
        self.combo_lock = threading.RLock()

        # Global pause state
        self.global_pause = False
        self.monitoring_was_active = False
        self.combo_was_running = False
        self.global_pause_lock = threading.RLock()

        # Trigger cooldown tracking
        self.last_trigger_times = {}

        # Inventory clear interrupt flag
        self.inventory_clear_interrupt = False

        # GUI minimize/restore state (shared between InventoryTab and close_app)
        self.gui_minimized_for_clear = False
        self.original_gui_geometry = None
        self.original_gui_state = None
        self.gui_was_foreground_before_minimize = True

    @property
    def config(self) -> Any:
        return self._app.config

    # --- Monitoring state ---

    def is_monitoring(self) -> bool:
        with self.monitoring_lock:
            return self.monitoring

    def set_monitoring(self, state: bool) -> None:
        with self.monitoring_lock:
            self.monitoring = state

    def wait_monitoring_stopped(self, timeout: float = 2.0) -> None:
        start_time = time.time()
        with self.monitoring_lock:
            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # --- Combo state ---

    def is_combo_running(self) -> bool:
        with self.combo_lock:
            return self.combo_running

    def set_combo_running(self, state: bool) -> None:
        with self.combo_lock:
            self.combo_running = state

    def wait_combo_stopped(self, timeout: float = 2.0) -> None:
        start_time = time.time()
        with self.combo_lock:
            if self.combo_thread and self.combo_thread.is_alive():
                self.combo_thread.join(timeout=max(0.1, timeout - (time.time() - start_time)))

    # --- Global pause state ---

    def is_global_pause(self) -> bool:
        with self.global_pause_lock:
            return self.global_pause

    def set_global_pause(self, state: bool) -> None:
        with self.global_pause_lock:
            self.global_pause = state
