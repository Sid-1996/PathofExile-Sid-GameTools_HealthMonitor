---
description: Quick understanding guide for the current Path of Exile automation tool project state
---

# Project Understanding - Path of Exile Automation Tool

## Project Overview

This is a Windows automation tool for Path of Exile workflows with these current feature areas:

- health/mana monitor with automatic trigger keys
- skill combo execution
- inventory clear and pickup helpers
- global hotkeys
- auto-click integration

## Current Runtime State

- The latest modularization recovery pass is functionally restored.
- The latest verified smoke-test round passed.
- `git push` is still locked pending final review.
- `src/` is the canonical source of truth.

## Current Architecture

The project is no longer accurately described as a pure single-file app, but it is also not fully modularized.

### Current Shape

- `src/health_monitor.py`
  - main entry
  - Tkinter UI composition
  - runtime orchestration
  - feature integration
- `src/config_manager.py`
  - config load/save helpers
- `src/language_system.py`
  - translation and language-pack helpers
- `src/utils.py`
  - shared runtime helpers, emergency cleanup, F12 support
- `src/custom_dialogs.py`
  - shared dialog behavior

### Important Constraint

- `src for DEVELOPER/` still exists for compatibility and packaging workflows.
- Do not treat `src for DEVELOPER/` as the primary source of truth.

## Canonical Structure

```text
Python POE/
├─ src/
│  ├─ health_monitor.py
│  ├─ config_manager.py
│  ├─ custom_dialogs.py
│  ├─ language_system.py
│  ├─ utils.py
│  ├─ language_packs.json
│  ├─ health_monitor_config.json          # runtime-generated user config
│  ├─ health_monitor_config.json.backup
│  └─ screenshots/                        # runtime-generated captures/previews
├─ src for DEVELOPER/                     # compatibility layer
├─ scripts/
├─ tools/
├─ docs/
├─ AGENTS.md
├─ PROJECT_STRUCTURE.md
├─ DEVELOPER_HANDBOOK.md
├─ README.md
└─ test_*.py
```

## Current File Facts

- `src/health_monitor.py` is currently about 10.5k lines, not the older size referenced in prior notes.
- `CustomMessageBox` and `HealthMonitor` line locations changed after recovery work; avoid relying on stale line numbers from older documents.
- `README_EN.md` is not currently present.
- `src/auto_click.exe` and `src/auto_click.ahk` are not currently present in this checkout.

## Key Runtime Behaviors

### Configuration

- Config is loaded through `ConfigManager`.
- `health_monitor.py` still maps config values into runtime/UI state.
- Old trigger types using `health` / `mana` are migrated to `HP` / `MP`.

### Language

- UI text comes from `src/language_packs.json`.
- Language switching is runtime-driven through the language system helpers.

### Hotkeys

Current hotkeys include:

- `F3`: inventory clear
- `F5`: return to hideout
- `F6`: pickup helper
- `F9`: global pause
- `F10`: monitor toggle
- `F12`: emergency close

### F12 / Emergency Close

- F12 is not just a normal UI close path.
- The app also relies on `utils.global_f12_handler()` for forced-exit safety behavior.

## Lifecycle-Sensitive Areas

The most fragile parts of the current app are:

- startup ordering
- config application into UI
- background thread shutdown
- Tk `after(...)` callback cleanup
- worker-to-UI callback boundaries

Recent recovery work specifically addressed:

- broken `load_config()` structure
- `self.config` initialization order before UI access
- stale `after(...)` callbacks during shutdown
- background thread interaction with Tk during close
- cp950 console failures from emoji-bearing `print(...)`

If you change lifecycle-sensitive code, do not stop at launch success. Re-check normal close behavior too.

## Development Workflow

### Basic Local Flow

1. `scripts/install_dependencies.bat`
2. `scripts/run_monitor.bat`
3. edit `src/`
4. validate targeted behavior
5. build/package only when needed

### Minimum Validation for Recovery-Sensitive Changes

- `python -m py_compile src/health_monitor.py`
- feature smoke test
- normal open -> operate -> close cycle
- verify no stale callback or background-thread Tk errors

## Build and Packaging Notes

- `tools/build.py` is the packaging source of truth.
- It still supports compatibility fallback behavior involving `src for DEVELOPER/`.
- Expected packaged assets include:
  - `GameTools_HealthMonitor.exe`
  - `auto_click.exe`
  - `language_packs.json`
  - `使用說明.md`
  - `啟動工具.bat`
  - `README.txt`

## Documentation Notes

- `README.md` exists.
- `README_EN.md` should not be referenced as if it already exists.
- `docs/` currently contains release notes, usage guides, and technical notes.

## Quick Orientation Summary

If you are new to this repo, the safest mental model is:

- edit `src/`
- compare against `src for DEVELOPER/` only when needed
- assume lifecycle code is fragile
- assume runtime-generated files under `src/` are not canonical source
- assume `git push` is disallowed until final review is explicitly cleared
