# AI Contributor Quick Guide

This file is for future AI/code agents to understand the project quickly and avoid breaking release flow.

## Project Goal

Windows automation tool for Path of Exile workflows:
- health/mana monitor
- skill combo
- inventory clear/pickup
- auto-click integration

## Canonical Structure

- `src/`: canonical source of truth for runtime code and language packs
- `src/config_manager.py`, `src/language_system.py`, `src/utils.py`, `src/custom_dialogs.py`, `src/skill_timer.py`: modularized components used by `src/health_monitor.py`
- `scripts/`: one-click local workflows
- `tools/build.py`: packaging pipeline (PyInstaller + package assembly)
- `docs/`: user/developer documentation

## One-Click Workflows

1. Install dependencies: `scripts/install_dependencies.bat`
2. Run from source: `scripts/run_monitor.bat`
3. Build EXE: `scripts/build_exe.bat`
4. Test built EXE: `scripts/test_built_exe.bat`

## Packaging Rules (Critical)

- Keep version consistent in `tools/build.py` (`APP_VERSION`).
- Build output should include:
  - `GameTools_HealthMonitor.exe`
  - `auto_click.exe`
  - `language_packs.json`
  - `使用說明.md`
  - `啟動工具.bat`
  - `README.txt`
- `tools/build.py` sources all assets from `src/`.
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

- Do not assume `README_EN.md` exists today. If bilingual public docs are required again, add or restore the English counterpart first.
