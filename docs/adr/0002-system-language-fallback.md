# ADR 0002: 系統語系偵測作為無偏好的預設

**Date:** 2026-08-29
**Status:** Accepted

## Context

先前無 `config.language` 時寫死 `zh-tw`，非中文 Windows 使用者首次啟動即見中文，需手動切換。
參考專案 `ocr-trigger-clicker` 在 `i18n.detect_system_language()` 以 `GetUserDefaultUILanguage & 0xFF` 對映
`0x04→zh_TW / 0x11→ja / 其他→en`，首次啟動即符合系統語系。

## Decision

- `language_system.detect_system_language()` + `_langid_to_code()`（`0x04→zh-tw`，其餘→`en`，`ja` 暫對映 `en` 因尚無包）。
- `app.py` 啟動在 `QApplication` 前決定初始語系：`cfg.get("language") or detect_system_language()` → `normalize_language_code` → `LanguageManager.change_language`。
- `config_manager._ensure_hotkeys` 的語言正規化統一經 `normalize_language_code`，大小寫/`zh_TW`/`zh-tw` 容錯。

## Alternatives Considered

- **維持寫死 `zh-tw`**：對海外使用者不友善。
- **引入 `locale.getdefaultlocale`**：在 Windows 上不如 `GetUserDefaultUILanguage` 準確（後者為 UI 語言）。

## Consequences

- 首次啟動即正確語系，無需手動切換；已有 `config` 的使用者不受影響（偏好優先）。
- 平台限制：非 Windows 下 `ctypes` 失敗時 fallback `en`。
