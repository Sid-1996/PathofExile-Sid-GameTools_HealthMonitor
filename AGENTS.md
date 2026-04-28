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
- `src for DEVELOPER/`: compatibility layer for legacy scripts/releases
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
- `tools/build.py` must prefer `src/` and fallback to `src for DEVELOPER/`.
- If PyInstaller cache is locked on Windows (`WinError 5`), clear `build/GameTools_HealthMonitor` and rebuild.

## Safety/Review Checklist Before Commit

- No secrets/tokens/private keys.
- No accidental mirror directories (e.g. duplicated project copies).
- README versions/links match current release state.
- Build + launch smoke test passes.

## Notes for Future Refactor

- `src for DEVELOPER/` can be removed only after all packaging and release scripts stop depending on it.
- Keep documentation bilingual (`README.md` + `README_EN.md`) when editing public-facing info.
