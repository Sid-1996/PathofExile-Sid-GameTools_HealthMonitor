# AI Contributor Quick Guide

This file is for future AI/code agents to understand the project quickly and avoid breaking release flow.

## Project Goal

Windows automation tool for Path of Exile workflows:
- health/mana monitor
- skill combo
- inventory clear/pickup
- auto-click integration

## Shell Environment

This project runs on Windows with **PowerShell 7+** available as the shell.
All commands in this file and related scripts assume PowerShell 7+ syntax (pipeline chain operators `&&` / `||`, `Set-Content`, `Get-ChildItem`, etc.).
Avoid `cmd.exe` batch idioms unless running explicit `.bat` scripts.

## Available Tools

The following tools are available in PATH and can be used by agents for searching and analysis:

- **ripgrep** (`rg 15.1.0`) — fast recursive search with PCRE2 support
  - Use `rg -C` for context around matches
  - Use `rg --count-matches` for precise match counting
  - Defaults to `.gitignore`-aware behavior

- **ruff** (`ruff 0.15.16`, via pipx) — fast Python linter + formatter
  - `ruff check src/` — scan for issues
  - `ruff check src/ --statistics` — summary view (good for large files)
  - `ruff check src/ --fix` — auto-fix safe issues (whitespace, f-string, etc.)
  - Config lives in `pyproject.toml` `[tool.ruff]`; aligned with existing `.flake8` rules
  - Known baseline: 591 issues in `health_monitor.py` (mostly whitespace, 31 bare-except, 11 complex functions)

- **pyright** (`pyright 1.1.410`, via pipx) — static type checker
  - `pyright src/health_monitor.py` — type-check main app
  - Useful before touching `close_app()`, threading code, or tkinter callbacks
  - No `pyrightconfig.json` yet — runs with defaults (basic mode)

- **py-spy** (`py-spy 0.4.2`, via pipx) — live profiler, no code changes needed
  - `py-spy top --pid <PID>` — see which functions are hot while app is running
  - `py-spy record -o profile.svg --pid <PID>` — flamegraph output
  - Requires running process PID; use `psutil` or Task Manager to find it

- **commitizen** (`cz 4.16.3`, via pipx) — structured commit messages + auto changelog
  - `cz commit` — interactive prompt instead of `git commit`
  - `cz bump` — auto-increment version in `health_monitor.py` + `build.py` + `CHANGELOG.md`
  - Config lives in `pyproject.toml` `[tool.commitizen]`
  - Conventional commit format: `feat:`, `fix:`, `refactor:`, `chore:` etc.

## When to Use Each Tool

**改任何 Python 之前**
→ 先跑 `ruff check src/ --statistics` 確認現有 baseline，不要把歷史包袱誤認為自己造成的

**改 `close_app()`、threading、tkinter callback 等敏感路徑之前**
→ 先跑 `pyright src/health_monitor.py`，確認型別沒有明顯錯誤再動手

**準備 commit**
→ 用 `cz commit` 取代 `git commit`（互動式選擇 feat/fix/refactor/chore 等類型）
→ 升版本號用 `cz bump`，它會自動同步 `health_monitor.py`、`build.py`、`CHANGELOG.md`，不要手動改三個地方

**收到效能問題回報（截圖卡頓、監控延遲）**
→ 請使用者跑起程式後，用 `py-spy top --pid <PID>` 觀察熱點函式
→ 要產出 flamegraph 給人看：`py-spy record -o profile.svg --pid <PID>`

**ruff 掃出問題時的處理原則**
→ `[*]` 標記 = 可自動修，直接 `ruff check src/ --fix` 處理（空白、f-string 等）
→ `E722` (bare-except) = 需人工判斷，確認是否應改為具體 exception 類型
→ `C901` (complex-structure) = 函式過複雜，列入重構待辦，不要在當次任務順手動它
→ `[ ]` 標記 = 無法自動修，需人工處理，視情況決定是否在當次任務處理

## Current Git State

- Branch: `master`
- Ahead of `origin/master` by **20 commits** (will be 21 after next commit)
- Working tree: **clean** after F821 fixes
- `git push` is **locked** — do not push unless explicitly instructed

## Recent Changes (v1.0.9 + pending)

### Activation-Aware Previews

- `monitor_health()` now checks `window.isActive` on every iteration.
- When the window loses focus, health/mana preview labels show "等待遊戲視窗激活" instead of capturing covered/desktop content.
- Manual capture methods (`capture_preview`, `capture_mana_preview`, async variants) all check `_is_game_window_active()` before capturing.
- Inventory preview refresh also checks activation state.
- Flat check (no busy-wait loop), 0.5s re-check interval.
- Helper: `_is_game_window_active()`, `_show_health_preview_placeholder()`, `_show_mana_preview_placeholder()`.

### Exclusion Marker Canvas Overlay

- Exclusion markers are drawn as a separate Canvas overlay (`_draw_exclusion_overlay`), independent of the background image.
- Click toggles exclusion via `_on_preview_click` → calls `_draw_exclusion_overlay()`.
- No full re-render of the inventory preview on exclusion toggle.

### Max Preview Size

- Default max_width: 500 → 700
- Default max_height: 400 → 500

### Known Issues / DXGI vs GDI

- `PrintWindow` (GDI) returns all-black frames for Path of Exile 2 (DirectX) — confirmed via test harness.
- `dxcam` (DXGI Desktop Duplication) captures the final composited desktop, so covered/minimized windows yield covered/desktop content — same as `mss`.
- No reliable capture-before-activation solution exists without Windows.Graphics.Capture (Win10+).
- Activation guard is the chosen mitigation path for now.

## Canonical Structure

- `src/`: single source of truth for runtime code and language packs
  - `health_monitor.py` (main app, ~10,400 lines)
  - `config_manager.py`, `language_system.py`, `utils.py`, `custom_dialogs.py`, `skill_timer.py`
  - `language_packs.json`, `使用說明.md`, `auto_click.exe`
- `scripts/`: one-click local workflows
- `tools/build.py`: packaging pipeline (PyInstaller + package assembly)
- `docs/`: user/developer documentation

Note: `src for DEVELOPER/` has been **removed**. All assets live in `src/` only.

## One-Click Workflows

1. Install dependencies: `scripts/install_dependencies.bat`
2. Run from source: `scripts/run_monitor.bat`
3. Build EXE: `scripts/build_exe.bat`
4. Test built EXE: `scripts/launch_built_exe.bat`

## Version

- Current: **v1.0.9**
- Single source: `src/_version.py` (`__version__ = "1.0.9"`)
- `health_monitor.py`: `CURRENT_VERSION = f"v{__version__}"`
- `build.py`: `APP_VERSION = __version__`
- Managed by commitizen via `src/_version.py:__version__`

## Packaging Rules (Critical)

- `tools/build.py` sources all assets from `src/`.
- Build output includes:
  - `GameTools_HealthMonitor.exe`, `auto_click.exe`, `language_packs.json`
  - `使用說明.md`, `啟動工具.bat`, `README.txt`
- If PyInstaller cache is locked on Windows (`WinError 5`), clear `build/GameTools_HealthMonitor` and rebuild.

## Safety/Review Checklist Before Commit

- No secrets/tokens/private keys.
- No accidental mirror directories (e.g. duplicated project copies).
- README versions/links match current release state.
- Build + launch smoke test passes.
- Stage only request-scoped files when the worktree is mixed.

## Close Lifecycle Notes

- `close_app()` is a sensitive path. Be careful with `_is_closing`, scheduled `after(...)` callbacks, and background threads.
- Background workers must not touch Tk widgets after shutdown begins.
- When modifying startup or shutdown logic, re-check normal close flow, not just app launch.

## Recent Cleanup History

- 29 messy commits squashed into 12 themed commits.
- ~185 lines of dead code removed from `health_monitor.py` (duplicate methods, uncalled functions, debug prints, commented-out blocks).
- `src for DEVELOPER/` removed; build pipeline simplified.
- Runtime-generated files (`screenshots/`, `health_monitor_config.json`) no longer tracked.
- `.windsurf/` workflow docs cleaned out.

## Notes for Future Refactor

- `health_monitor.py` at ~10,500 lines is the main refactor target.
- Inventory exclusion feature: `excluded_inventory_slots` (set of ints), saved as `excluded_inventory_slots` in config JSON, rendered as blue overlay on preview, respected in all F3 clear paths.
- `_on_preview_click()` handles Canvas click → toggle exclusion → re-render.
- `_preview_meta` stores rendered image dimensions for click coordinate mapping.
- No automated test suite exists yet — manual diagnostic scripts were removed.
- Do not assume `README_EN.md` exists today. If bilingual public docs are required again, add or restore the English counterpart first.
