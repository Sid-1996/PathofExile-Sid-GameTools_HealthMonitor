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

## Current Git State

- Branch: `master`
- Ahead of `origin/master` by **16 commits** (will be 17 after next commit)
- Working tree: **dirty** (modified `src/health_monitor.py`)
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
- Set in `src/health_monitor.py` (`CURRENT_VERSION`) and `tools/build.py` (`APP_VERSION`)

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
