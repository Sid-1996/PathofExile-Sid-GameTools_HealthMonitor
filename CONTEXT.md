# CONTEXT.md — GameTools Health Monitor Glossary

> 僅詞彙定義，無實作細節。實作決策見 `docs/adr/`。

Windows 上給 Path of Exile 玩家的日常自動化工具領域詞彙。

## Language

**LanguagePreference**:
使用者已持久化的語系偏好，優先於系統語系。
_Avoid_: 設定語系（泛用）

**SystemLanguage**:
首次啟動、無 `LanguagePreference` 時的預設語系。
_Avoid_: 預設語系（泛用）

**LanguageCode**:
正規化後的語系代碼，值域 `zh-tw` / `en`。
_Avoid_: locale、lang

**LanguageDisplayName**:
使用者可見的選項文案，`繁體中文 ↔ zh-tw` / `English ↔ en`。
_Avoid_: 語系名稱（泛用）

**TranslationCatalog**:
`key→字串` 映射，缺 key 時 fallback 至 `zh-tw`。
_Avoid_: 語系包、language packs

**RestartRequiredSetting**:
變更後需重啟才完全生效的設定。
_Avoid_: 需要重啟（泛用）

**Relaunch**:
分離程序重啟，新程序等舊程序退出才初始化。
_Avoid_: 重啟（泛用）

## Game Window

**GameWindowTitle**:
使用者指定的遊戲視窗標題，單一來源。
_Avoid_: window_title、inventory_window_title、window_var（遺留）

**Foreground**:
目前作用的遊戲視窗，可截取、可操控。
_Avoid_: active window（作為正式詞時）

**Background**:
未最小化的非作用視窗，可截取、不可操控；包含被遮擋與失焦。
_Avoid_: Occluded、後台視窗

**Minimized**:
視窗已最小化，不可截取。
_Avoid_: 最小化（泛用）

**Missing**:
視窗不存在，不可截取、不可操控。
_Avoid_: 視窗關閉（泛用）

**MonitorRegion**:
Health / Mana 監控用的相對視窗矩形，絕對座標。
_Avoid_: region（泛用）

**InventoryRegion**:
背包專用的相對視窗矩形，絕對座標。
_Avoid_: region（泛用）

**CaptureResult**:
視窗區域截取結果：`("wgc" | "mss" | None)`。`"wgc"` 為 Background 可截結果，`"mss"` 為僅 Foreground 可截結果；`None` 涵蓋視窗 `Missing` / `Minimized` / WGC 不可用且非 Foreground。呼叫端不分支 `backend`。
_Avoid_: valid 布林、backend 分支

## Health / Mana Monitor

**HealthManaMonitor**:
只負責 Health / Mana 分析與吃藥觸發，不含 Combo 與 Inventory。
_Avoid_: Monitor（泛用）、AutomationController

**HealthPercent / ManaPercent**:
Health / Mana 的百分比值，值域 0–100。
_Avoid_: 血量、魔力（泛用）

## Combo

**ComboExecution**:
一輪連招執行；前景失效立即取消，回到 Idle。
_Avoid_: 暫停續跑、連招暫停

## Inventory

**ClearInventory**:
正式清包動作。
_Avoid_: quick_clear、清包（泛用）

**TestClear**:
測試清包動作，非正式操作。
_Avoid_: test_clear（作為正式詞時）
