# ADR 0001: 語言切換改為重啟生效

**Date:** 2026-08-29
**Status:** Accepted

## Context

`FluentWindow`（qfluentwidgets 1.11.3）導航項無運行期公開 API 可刷新文字。
先前 `MainWindow.change_language_display` 試圖逐 Tab 呼叫 `update_language()` 熱更新，
結果導航、分頁標題殘留舊語系，需重啟才一致，且每個 Tab 需各自維護刷新邏輯，維護成本高。

參考專案 `ocr-trigger-clicker` 已驗證「詢問→分離程序重啟」模式可 100% 保證語系一致。

## Decision

- 語言切換列為 `RestartRequiredSetting`，任何 `language` 變更走「詢問是否立即重啟 → `Popen(detached)` + `--wait-exit-pid` + `os._exit`」。
- `QMessageBox.question(Yes|No)`：Yes 立即 `relaunch`，No 僅寫入 `config`、下次啟動生效。
- 逐 Tab 的 `update_language()` 調用從 `change_language_display` 移除（函式保留作相容，但不再作為熱更新手段）。

## Alternatives Considered

- **純熱更新**：需為 FluentWindow 寫 hack 或 fork 套件，且每次新增文案都要補刷新，YAGNI/脆弱。
- **雙軌（熱更新 + 橫幅提示重啟）**：UI 複雜、使用者仍見半中半英狀態。

## Consequences

- 正面：語系 100% 一致、程式碼減少、與 `ocr-trigger-clicker` 行為一致。
- 負面：切換語言多一次重啟（使用者可選 No 延後）；需處理 `config` 同步落盤與 `velopack` 時序。
- 遷移：`app.py` 啟動加入 `_wait_exit_pid_arg()`（`velopack` 之前），`MainWindow` 加入 `_relaunch_detached()` 與 watchdog。
