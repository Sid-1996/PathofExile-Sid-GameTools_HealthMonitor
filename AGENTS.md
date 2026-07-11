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
  - Current baseline: 11 `C901` `complex-structure` errors in `health_monitor.py`
  - Resolved: all `E722` (bare-except), `F821` (undefined-name), `E402` (import-order) — zero remaining

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
  - `cz bump` — auto-increment version in `_version.py` + `build.py` + `CHANGELOG.md`
  - Config lives in `pyproject.toml` `[tool.commitizen]`
  - Conventional commit format: `feat:`, `fix:`, `refactor:`, `chore:` etc.

## When to Use Each Tool

**Before editing any Python**
→ run `ruff check src/ --statistics` to confirm the existing baseline; don't mistake pre-existing issues for your own

**Before touching `close_app()`, threading, or tkinter callbacks**
→ run `pyright src/health_monitor.py` to catch type errors first

**Before committing**
→ `ruff check src/ --fix && ruff format src/` to auto-fix safe issues
→ use `cz commit` instead of `git commit` for structured messages
→ use `cz bump` to increment version — it syncs `_version.py`, `build.py`, `CHANGELOG.md` automatically

**When ruff reports issues**
→ `[*]` = auto-fixable, run `ruff check src/ --fix`
→ `E722` (bare-except) = manual review needed
→ `C901` (complex-structure) = pre-existing, add to refactor backlog, do not touch in current task
→ `[ ]` = manual fix, decide case by case

**When a performance issue is reported**
→ `py-spy top --pid <PID>` to find hot functions
→ `py-spy record -o profile.svg --pid <PID>` for a flamegraph

## Canonical Structure

```text
src/                          # Single source of truth for runtime code
scripts/                      # One-click local workflows
tools/build.py                # PyInstaller packaging pipeline
docs/                         # User-facing documentation
.github/workflows/ci.yml      # Lint + type check on push/PR
latest_version.txt            # Raw GitHub version check (no API limit)
release.ps1                   # One-click publish script
updater_main.py               # Standalone updater process (built to updater.exe)
```

### src/ Module Responsibilities

| Module | Role | Lines | Dependencies |
|---|---|---|---|
| `health_monitor.py` | Main entry, UI orchestration, event loop | ~2,042 | All other modules |
| `monitor_analyzer.py` | Health/mana HSV analysis, trigger logic | 349 | cv2, numpy |
| `capture_utils.py` | Screenshot capture, mss singleton | 72 | mss, PIL, numpy |
| `image_utils.py` | Image drawing, resizing, preview utilities | 203 | PIL |
| `inventory_utils.py` | Inventory slot analysis, item detection | 95 | numpy |
| `config_manager.py` | JSON config load/save with backup | 208 | none |
| `custom_dialogs.py` | Modal dialogs with dynamic sizing | 215 | tkinter |
| `language_system.py` | Bilingual string lookup | 144 | JSON |
| `skill_timer.py` | Skill cooldown timer module | 432 | tkinter |
| `utils.py` | Emergency cleanup, F12 handler, Tooltip | 166 | keyboard, psutil |
| `tab_inventory.py` | Inventory clear + pickup UI + logic | 3,628 | cv2, numpy, PIL, mss, pyautogui |
| `tab_monitor.py` | Health/mana monitor tab UI + logic | 1,647 | cv2, numpy, PIL, mss, keyboard |
| `tab_version.py` | Version check + in-app download/update | 402 | requests, updater_core |
| `tab_about.py` | About tab, sponsor/donate buttons | ~200 | tkinter |
| `app_state.py` | Shared application state container | ~100 | none |
| `auto_click_manager.py` | Auto-click management (AHK) | ~150 | subprocess, psutil |
| `usage_tracker.py` | Usage time statistics | ~100 | none |
| `window_key_sender.py` | Window-focused key sending | ~80 | pygetwindow, pyautogui |

Root-level modules (not in src/):

| Module | Role | Dependencies |
|---|---|---|
| `updater_core.py` | Update engine: version check, download, apply | requests, zipfile |
| `updater_main.py` | Standalone updater process (built to updater.exe) | ctypes, subprocess |
| `latest_version.txt` | Raw GitHub version string for update checks | — |

Runtime-generated files — do not treat as source:
- `src/health_monitor_config.json` (user config state)
- `src/health_monitor_config.json.backup`
- `src/screenshots/`

## One-Click Workflows

1. Install dependencies: `scripts/install_dependencies.bat`
2. Run from source or EXE: `Run.bat`
3. Build EXE: `scripts/build_exe.bat`
4. Test built EXE: `Run.bat`

## Version

- Current: **v1.2.1**
- Single source: `src/_version.py` (`__version__ = "1.2.1"`)
- `health_monitor.py`: `CURRENT_VERSION = f"v{__version__}"`
- `build.py`: `APP_VERSION = __version__`
- Managed by commitizen via `src/_version.py:__version__`

## Packaging Rules (Critical)

- `tools/build.py` sources all assets from `src/`.
- Build output includes:
  - `GameTools_HealthMonitor.exe`, `auto_click.exe`, `updater.exe`, `language_packs.json`
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

## Notes for Future Refactor

- `health_monitor.py` at ~2,042 lines (down from ~9,842) is the main refactor target. Remaining 11 `C901` warnings are pre-existing complex functions.
- Inventory exclusion feature: `excluded_inventory_slots` (set of ints), saved in config JSON, rendered as blue overlay on preview, respected in all F3 clear paths.
- `_on_preview_click()` handles Canvas click → toggle exclusion → re-render.
- `_preview_meta` stores rendered image dimensions for click coordinate mapping.
- No automated test suite exists yet.
- Do not assume `README_EN.md` exists. If bilingual public docs are required, add it explicitly.

## Known Issues

- `PrintWindow` (GDI) returns all-black frames for Path of Exile 2 (DirectX).
- `dxcam` / `mss` both capture the composited desktop — covered/minimized windows yield desktop content, not game content.
- Activation guard (`_is_game_window_active()`) is the current mitigation; no reliable capture-before-activation solution without Windows.Graphics.Capture (Win10+).
