"""skill_timer.py（Qt 版）SkillSlot 計時迴圈測試。"""

import time


def test_skill_slot_validation():
    from qt.skill_timer import SkillSlot

    slot = SkillSlot()
    assert slot.start() is False  # 空 key 不合法
    slot.key = "q"
    slot.interval_ms = 10
    assert slot.start() is False  # 低於最低間隔不合法
    slot.stop()


def test_skill_slot_loop_sends_keys(monkeypatch):
    from qt import skill_timer as st

    pressed = []

    class FakePG:
        @staticmethod
        def press(k):
            pressed.append(k)

        @staticmethod
        def hotkey(*args):
            pressed.append("+".join(args))

    monkeypatch.setattr(st, "pyautogui", FakePG(), raising=False)
    monkeypatch.setattr(st, "_PYAUTOGUI_OK", True)

    slot = st.SkillSlot()
    slot.key = "q"
    slot.interval_ms = 50
    assert slot.start() is True
    try:
        deadline = time.time() + 2.0
        while time.time() < deadline and not pressed:
            time.sleep(0.02)
        assert pressed, "timer loop never fired"
        assert pressed[0] == "q"
    finally:
        slot.stop()
