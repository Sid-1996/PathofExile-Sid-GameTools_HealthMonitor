"""auto_update.py — Velopack 自動更新薄包裝。

取代自製 updater_core 的檢查/下載/套用三段流程：
- 更新源：GitHub Releases（GithubSource）
- 非 Velopack 安裝環境（開發原始碼、舊版 ZIP 解壓）→ create_manager() 回傳 None
- 版本資訊以 InfoShim 暴露 .version，讓呼叫端（qt/version.py）與舊介面形狀一致
"""

import velopack

GITHUB_REPO_URL = "https://github.com/Sid-1996/PathofExile-Sid-GameTools_HealthMonitor"


class AutoUpdateError(RuntimeError):
    """帶語言 key 的使用者可見更新錯誤（沿用 updater_core.UpdateError 形狀）。"""

    def __init__(self, key, **params):
        self.key = key
        self.params = params
        super().__init__(key)


class UserCancelledError(RuntimeError):
    """相容舊介面保留；Velopack 下載不支援取消，此例外現階段不會被拋出。"""


class InfoShim:
    """包裝 velopack UpdateInfo，暴露 .version 供 UI 使用；apply 時取回原始物件。"""

    def __init__(self, raw_info):
        self._raw = raw_info
        self.version = str(raw_info.TargetFullRelease.Version)

    @property
    def is_downgrade(self):
        return bool(self._raw.IsDowngrade)


def is_not_installed_error(e: Exception) -> bool:
    """非 Velopack 安裝環境（開發/portable）跑更新操作時的辨識。

    velopack py 綁定對「未安裝」會拋 NotInstalledException 或帶
    'not properly installed' 訊息的 RuntimeError，兩者皆須涵蓋。
    """
    return "NotInstalled" in type(e).__name__ or "not properly installed" in str(e)


def create_manager(explicit_channel=None):
    """建立 UpdateManager；非安裝環境或發生任何初始化問題時回傳 None。

    explicit_channel：使用者勾選搶先版時傳 "beta"；預設跟隨安裝時的 channel。
    """
    try:
        source = velopack.GithubSource(GITHUB_REPO_URL)
        options = None
        if explicit_channel:
            # UpdateOptions(AllowVersionDowngrade, MaximumDeltasBeforeFallback, ExplicitChannel)
            # 勾選搶先版要能切到 beta（版本可能高於 stable），允許 downgrade 以便切回
            options = velopack.UpdateOptions(True, 10, explicit_channel)
        return velopack.UpdateManager(source, options)
    except Exception as e:
        if is_not_installed_error(e):
            return None  # 開發/portable 環境的正常情況，靜默降級
        print(f"[WARN] UpdateManager 初始化失敗: {e}")
        return None


def check_for_update(manager, allow_prerelease=False):
    """檢查更新；回傳 InfoShim 或 None（已最新）。未安裝環境回傳 None。"""
    if manager is None:
        return None
    try:
        info = manager.check_for_updates()
    except Exception as e:
        if is_not_installed_error(e):
            return None
        raise
    return InfoShim(info) if info else None


def download_update(manager, info, progress_cb=None):
    """下載更新（delta 由 Velopack 自動處理）。info 為 check_for_update 回傳的 InfoShim。"""
    manager.download_updates(info._raw, progress_callback=progress_cb)


def apply_and_restart(manager, info):
    """套用更新並重啟應用程式（成功時不會返回，程序由 Velopack 接管重啟）。"""
    manager.apply_updates_and_restart(info._raw)


def is_packaged_for_updates():
    """是否具備 Velopack 更新能力（vpk 打包並經 Setup.exe 安裝）。"""
    return create_manager() is not None


if __name__ == "__main__":
    # self-check：開發機上必為非安裝環境，檢查操作需優雅降級為「無更新」而非爆炸
    mgr = create_manager()
    assert check_for_update(mgr) is None, "未安裝環境的 check 應回傳 None"

    class _NotInstalled(Exception):
        pass

    assert is_not_installed_error(_NotInstalled()), "NotInstalled 辨識失敗"
    assert not is_not_installed_error(ValueError("x")), "一般例外不應誤判"
    assert is_not_installed_error(RuntimeError("This application is not properly installed: x")), "訊息式辨識失敗"

    shim = InfoShim(type("_FakeInfo", (), {"TargetFullRelease": type("_A", (), {"Version": "1.2.3"})(), "IsDowngrade": False})())
    assert shim.version == "1.2.3" and not shim.is_downgrade, "InfoShim 包裝失敗"

    print("auto_update self-check OK")
