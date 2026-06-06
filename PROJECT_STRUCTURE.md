# GameTools Health Monitor - Project Structure

## Current Project Layout

```text
Python POE/
├─ .github/                         # GitHub metadata and workflows
├─ .windsurf/                       # Workflow notes and SOPs
├─ assets/                          # Static assets
├─ build/                           # Local build artifacts
├─ dist/                            # Packaged outputs
├─ docs/                            # User/developer documentation
├─ scripts/                         # One-click local workflows
├─ src/                             # Canonical runtime source
│  ├─ health_monitor.py             # Main application entry and integration layer
│  ├─ config_manager.py             # Config loading/saving helpers
│  ├─ language_system.py            # Language pack loading and translation helpers
│  ├─ utils.py                      # Shared runtime utilities and F12 cleanup helpers
│  ├─ custom_dialogs.py             # Shared dialog helpers
│  ├─ skill_timer.py                # Skill timer module with bilingual support
│  ├─ language_packs.json           # Bilingual UI strings
│  ├─ health_monitor_config.json    # User config (runtime-generated)
│  ├─ health_monitor_config.json.backup
│  ├─ screenshots/                  # Runtime-generated screenshots and previews
│  └─ __pycache__/
├─ tools/                           # Build pipeline and icon
├─ AGENTS.md                        # AI contributor quick guide
├─ CHANGELOG.md                     # Change history
├─ DEVELOPER_HANDBOOK.md            # Detailed technical documentation
├─ LOCAL_DEVELOPMENT.md             # Local setup notes
├─ PROJECT_STRUCTURE.md             # This file
├─ README.md                        # Primary public README
├─ LICENSE
├─ GameTools_HealthMonitor.spec
└─ test_*.py                        # Local validation scripts
```

## Canonical Source Rules

- Edit runtime code in `src/`.
- Treat `src/` as the single source of truth.
- Do not assume runtime-generated files under `src/` are stable source files.

## Important Runtime Files

- `src/health_monitor.py` remains the main application file and orchestration layer.
- `src/config_manager.py`, `src/language_system.py`, `src/utils.py`, and `src/custom_dialogs.py` are active modularized components used by the main app.
- `src/health_monitor_config.json` is user/runtime state, not a canonical source file.
- `src/screenshots/` contains runtime-generated captures and should not be treated as stable source content.

## Scripts

- `scripts/install_dependencies.bat`: install Python dependencies
- `scripts/run_monitor.bat`: run from source
- `scripts/build_exe.bat`: build EXE package
- `scripts/launch_built_exe.bat`: launch packaged EXE for smoke test
- `scripts/cleanup.bat`: cleanup helper
- `scripts/pre-push-check.bat`: pre-push checks
- `scripts/push-with-review.bat`: guarded publish helper
- `scripts/release.bat`, `scripts/secure-release.bat`: release-oriented helpers
- `scripts/GameTools_HealthMonitor_Light.bat`: lightweight launcher

## Tools

- `tools/build.py` is the packaging source of truth.
- `tools/GameTools_HealthMonitor.ico` is the application icon.

## Documentation Notes

- `README.md` exists.
- `README_EN.md` is not currently present and should not be referenced as if it already exists.
- `docs/` currently includes release notes, usage guides, and architecture notes.

## Version Notes

- Current verified app version is `v1.0.8` in `src/health_monitor.py`.
- Current packaging version is `1.0.8` in `tools/build.py`.

## Packaging Notes

- Packaging is driven solely by `tools/build.py` sourcing from `src/`.
- Expected packaged assets include:
  - `GameTools_HealthMonitor.exe`
  - `auto_click.exe`
  - `language_packs.json`
  - `使用說明.md`
  - `啟動工具.bat`
  - `README.txt`

## Current Status

- Modularization recovery completed — all helper modules are functionally independent.
- 29 commits squashed to 9 themed commits for clean history.
- Smoke tests passed in the latest verified round.
- `git push` remains locked pending final review.
