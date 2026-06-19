# Health Monitor Developer Handbook

## Overview

This project is a Windows automation tool for Path of Exile workflows. The current feature set includes:

- health/mana monitoring with automatic key triggers
- skill combo execution
- inventory clear / pickup helpers
- global hotkeys
- auto-click integration

For project structure, module responsibilities, and available tooling, see `AGENTS.md`.

## Main Application Structure

### `health_monitor.py`

`health_monitor.py` is the integration layer (~9,800 lines). It imports all modularized helpers and owns:

- Tkinter root and UI composition
- notebook tabs and controls
- monitor/combo/inventory feature wiring
- startup sequencing
- config application into UI state
- shutdown lifecycle

### Key Classes

- `CustomMessageBox` — shared modal dialog wrapper
- `HealthMonitor` — main application controller

## Important Runtime Concepts

### Configuration

Configuration is stored in `src/health_monitor_config.json` (runtime state, not canonical source).

- Loaded through `ConfigManager`
- `health_monitor.py` maps loaded config into runtime/UI state
- Old config entries using `health` / `mana` are migrated to `HP` / `MP`

Common config areas: monitor regions, trigger settings, inventory regions and colors, combo settings, language, window geometry, preview settings.

### Language System

UI text comes from `src/language_packs.json`.

- Default runtime language is managed by `language_system.py`
- UI strings should use language keys via `get_text()`, not hardcoded text
- Language switching works at runtime; app must be restarted to apply

### Hotkeys

| Key | Action |
|---|---|
| F3 | Inventory clear flow |
| F5 | Return to hideout |
| F6 | Pickup helper |
| F9 | Global pause |
| F10 | Toggle monitoring |
| F12 | Emergency close (safety path via `utils.global_f12_handler()`) |

F12 is intentionally a forced-exit fallback, not just a normal close button.

## Threading and Lifecycle

### Active Background Work

- health/mana monitoring loop
- combo execution
- mouse interrupt monitoring
- version check worker callbacks
- preview/update helpers

### Close Lifecycle

Shutdown is a sensitive area. Current expectations:

- `_is_closing` must be set early in close flow
- pending `after(...)` callbacks must be treated carefully
- background threads must not touch Tk widgets after shutdown starts
- UI callbacks scheduled from worker threads must be closing-aware

Any future work touching startup or shutdown logic must re-test:
- app launch and smoke flow
- normal close flow
- callback/thread cleanup after close

Specific things to verify when modularization or cleanup code is touched:
- no `invalid command name` errors from stale Tk callbacks
- no `RuntimeError: main thread is not in main loop`
- no background worker updating destroyed widgets

## Development Workflow

### Recommended Local Flow

1. Install dependencies: `scripts/install_dependencies.bat`
2. Run locally: `scripts/run_monitor.bat`
3. Make request-scoped code changes in `src/`
4. Validate with targeted checks (see below)
5. Build/package only when needed: `scripts/build_exe.bat`

### Minimum Validation for Runtime Changes

```
python -m py_compile src/health_monitor.py
ruff check src/ --fix && ruff format src/
```

Then: targeted smoke test for the changed feature + normal launch/close verification.

When lifecycle-sensitive code changes, also verify:
- no stale Tk callback errors
- no thread-safety issues on close

### Source of Truth Rules

- `src/` is the single source of truth. Edit runtime code only here.
- Do not stage runtime-generated files in mixed worktrees:
  - `src/health_monitor_config.json`
  - `src/health_monitor_config.json.backup`
  - `src/screenshots/`
