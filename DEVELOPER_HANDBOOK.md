# Health Monitor Developer Handbook

## Overview

This project is a Windows automation tool for Path of Exile workflows. The current feature set includes:

- health/mana monitoring with automatic key triggers
- skill combo execution
- inventory clear / pickup helpers
- global hotkeys
- auto-click integration

The project is still centered around `src/health_monitor.py`, but part of the codebase has already been modularized into helper modules under `src/`.

## Current Architecture

### Main Runtime Files

- `src/health_monitor.py`
  - main application entry
  - Tkinter UI
  - feature orchestration
  - thread startup / shutdown flow
- `src/config_manager.py`
  - config persistence helpers
- `src/language_system.py`
  - language pack loading and translation lookup
- `src/utils.py`
  - shared runtime helpers
  - cleanup helpers
  - F12 emergency-close support
- `src/custom_dialogs.py`
  - shared dialog behavior

### Project State

- `src/` is the canonical source of truth.
- `src for DEVELOPER/` still exists for packaging compatibility and legacy workflows.
- `tools/build.py` still depends on compatibility behavior and cannot yet assume a pure single-source build.

## Main Application Structure

### `health_monitor.py`

`health_monitor.py` remains the integration layer. It imports the modularized helpers and still owns:

- Tkinter root and UI composition
- notebook tabs and controls
- monitor/combo/inventory feature wiring
- startup sequencing
- config application into UI state
- shutdown lifecycle

### Key Classes

- `CustomMessageBox`
  - shared modal dialog wrapper used by the app
- `HealthMonitor`
  - main application controller

## Important Runtime Concepts

### Configuration

Configuration is stored in `src/health_monitor_config.json`.

Key points:

- runtime config is not canonical source code
- config is loaded through `ConfigManager`
- `health_monitor.py` still maps loaded config into runtime/UI state
- old config entries using `health` / `mana` are migrated to `HP` / `MP`

Common config areas:

- monitor regions
- trigger settings
- inventory regions and colors
- combo settings
- language
- window geometry
- preview settings

### Language System

UI text comes from `src/language_packs.json`.

Key points:

- default runtime language is managed by `language_system.py`
- UI strings should use language keys, not hardcoded text where practical
- language switching is expected to work at runtime

### Build and Packaging

Packaging is driven by `tools/build.py`.

Current packaging assumptions:

- prefer `src/`
- fallback to `src for DEVELOPER/` where needed
- package expected release assets such as:
  - `GameTools_HealthMonitor.exe`
  - `auto_click.exe`
  - `language_packs.json`
  - `使用說明.md`
  - `啟動工具.bat`
  - `README.txt`

Current runtime note:

- `src/auto_click.exe` and `src/auto_click.ahk` are not currently present in this checkout
- missing auto-click assets should be treated as runtime/package availability issues, not automatic proof that modularization is broken

## Hotkeys

The current hotkey set includes:

- `F3`: inventory clear flow
- `F5`: return to hideout
- `F6`: pickup helper
- `F9`: global pause
- `F10`: toggle monitoring
- `F12`: emergency close path

Important note:

- `F12` is intentionally a safety path, not just a normal UI close button
- the runtime includes a forced-exit fallback through `utils.global_f12_handler()`

## Threading and Lifecycle

### Active Background Work

The app uses background work for things such as:

- health/mana monitoring
- combo execution
- mouse interrupt monitoring
- version check worker callbacks
- preview/update helpers

### Close Lifecycle

Shutdown is a sensitive area.

Current expectations:

- `_is_closing` must be set early in close flow
- pending `after(...)` callbacks must be treated carefully
- background threads must not keep touching Tk widgets after shutdown starts
- UI callbacks scheduled from worker threads must be closing-aware

Recent recovery work specifically fixed issues around:

- `load_config()` recovery after modularization damage
- `self.config` initialization order before UI access
- `silent_version_check` / usage-time callback cleanup
- background thread interaction with Tk during close
- cp950 terminal failures from emoji-bearing `print(...)`

Any future work that changes startup or shutdown logic must re-test:

- app launch
- smoke flow
- normal close flow
- callback/thread cleanup after close

## Development Workflow

### Recommended Local Flow

1. Install dependencies with `scripts/install_dependencies.bat`
2. Run locally with `scripts/run_monitor.bat`
3. Make request-scoped code changes in `src/`
4. Validate with targeted checks
5. Build/package only when needed

### Minimum Validation for Runtime Changes

- `python -m py_compile src/health_monitor.py`
- targeted smoke test for changed feature
- normal launch and close verification when lifecycle-sensitive code changes

When modularization or cleanup code is touched, also verify:

- no `invalid command name` errors from stale Tk callbacks
- no `RuntimeError: main thread is not in main loop`
- no background worker trying to update destroyed widgets

## Source of Truth Rules

- edit `src/` first
- treat `src for DEVELOPER/` as compatibility-only
- do not overwrite `src/` from `src for DEVELOPER/` casually
- do not stage unrelated runtime-generated files in mixed worktrees

Examples of runtime-generated or user-state files that need extra care:

- `src/health_monitor_config.json`
- `src/health_monitor_config.json.backup`
- files under `src/screenshots/`

## Documentation Status

- `README.md` exists
- `README_EN.md` is not currently present
- if bilingual public documentation is required again, the English counterpart must be added or restored explicitly

## Release Status Note

The latest verified recovery pass is functionally restored and smoke-tested, but `git push` is still locked pending final review.

This handbook should describe the current verified state, not the pre-recovery broken state.
