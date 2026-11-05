# ADR 0003: 以 Locale 名稱區分簡繁中文系統語系

**Date:** 2026-11-05
**Status:** Accepted

## Context

ADR 0002 以 `GetUserDefaultUILanguage & 0xFF` 對映中文（0x04）一律回 `zh-tw`。
簡體中文包（zh-cn）加入後，簡中系統仍會被誤偵測為繁中，無法首次啟動即正確顯示。

LANGID 低位元組 0x04 無法區分 zh-CN / zh-TW / zh-HK，需更細的 locale 資訊。

## Decision

- `detect_system_language()` 優先讀 `GetUserDefaultLocaleName`，經 `_locale_name_to_code()` 區分：
  - `zh-cn` / `zh-hans*` / `zh-sg` → `zh-cn`
  - `zh-tw` / `zh-hk` / `zh-hant*` → `zh-tw`
  - `en*` → `en`
  - 其餘 → fallback LANGID
- LANGID fallback 保留並精細化：`0x0804`（zh-CN）、`0x1004`（zh-SG）→ `zh-cn`，其餘中文 → `zh-tw`
- `normalize_language_code()` 同步擴充：`zh-cn` / `zh-hans` / `zh-sg` / `zh-hant` / `zh-hk` 皆正規化，大小寫與 `_` / `-` 容錯
- `LanguageManager.language_display_map` 新增「简体中文」→ `zh-cn`

## Alternatives Considered

- **只加簡中包，不改偵測**：使用者需手動切換，首次啟動仍錯誤，體驗不完整。
- **改用 `locale.getdefaultlocale`**：Windows 上不如 `GetUserDefaultLocaleName` 準確，且可能回傳統 Big5 而非 BCP47。

## Consequences

- 簡中系統首次啟動即顯示簡中，繁中系統維持繁中，已有 `config.language` 偏好者不受影響。
- 平台限制：非 Windows 下 `ctypes` 失敗時 fallback `en`；`GetUserDefaultLocaleName` 不可用時回退 LANGID 判斷。
