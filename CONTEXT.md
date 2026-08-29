# CONTEXT.md — GameTools Health Monitor Glossary

> 僅詞彙定義，無實作細節。實作決策見 `docs/adr/`。

## Glossary

| Term | Definition |
|---|---|
| **LanguagePreference** | 使用者已持久化的語系偏好，存於 `health_monitor_config.json#language`，優先於系統語系。 |
| **SystemLanguage** | 首次啟動、無 `LanguagePreference` 時的預設語系；由 Windows `GetUserDefaultUILanguage` 的 Primary LANGID 決定（`0x04→zh-tw`，其他→`en`）。 |
| **LanguageCode** | 正規化後的語系代碼，值域 `zh-tw` / `en`；大小寫與 `zh_TW`/`zh-tw` 等變體經 `normalize_language_code` 統一。 |
| **LanguageDisplayName** | 使用者可見的選項文案，`繁體中文 ↔ zh-tw` / `English ↔ en`。 |
| **TranslationCatalog** | `language_packs.json` 中的 `key→字串` 映射；缺 key 時 fallback 至 `zh-tw` 並 `warnings.warn`。 |
| **RestartRequiredSetting** | 變更後需重啟才完全生效的設定；`language` 為典型，FluentWindow 導航等無運行期 API 需重建。 |
| **Relaunch** | 分離程序重啟：舊程序 `Popen(detached)` 新程序並帶 `--wait-exit-pid=old_pid`，新程序等舊 PID 退出後才初始化，避免檔案鎖/單一實例衝突。 |
