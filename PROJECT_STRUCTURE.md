# GameTools Health Monitor - Project Structure

## Current Project Layout

```text
Python POE/
  ├─ .github/                         # GitHub metadata and workflows
  │  └─ workflows/
  │     ├─ ci.yml                     # Lint (ruff) + type check (pyright)
  │     ├─ release.yml                # Auto build + publish on tag
  │     └─ release-secure.yml         # Secure variant
  ├─ assets/                          # Static assets
  ├─ docs/                            # User/developer documentation
  ├─ scripts/                         # One-click local workflows
  │  ├─ auto_click.ahk                # AutoHotkey source for auto-clicker
  │  ├─ requirements.txt              # Python dependencies
  │  └─ *.bat                         # Workflow launchers
  ├─ src/                             # Canonical runtime source
  │  ├─ health_monitor.py             # Main application (~9,800 lines)
  │  ├─ capture_utils.py              # Screenshot capture helpers (72 lines)
  │  ├─ config_manager.py             # Config loading/saving (208 lines)
  │  ├─ custom_dialogs.py             # Custom message box dialogs (215 lines)
  │  ├─ image_utils.py                # Image processing utilities (203 lines)
  │  ├─ inventory_utils.py            # Inventory analysis functions (95 lines)
  │  ├─ language_system.py            # Translation system (144 lines)
  │  ├─ monitor_analyzer.py           # Health/mana analysis engine (349 lines)
  │  ├─ skill_timer.py                # Skill timer module (432 lines)
  │  ├─ utils.py                      # Runtime utilities + cleanup (166 lines)
  │  ├─ language_packs.json           # Bilingual UI strings
  │  └─ _version.py                   # Single version source
  ├─ tools/                           # Build pipeline and icon
  │  ├─ build.py                      # PyInstaller packaging
  │  └─ GameTools_HealthMonitor.ico   # Application icon
  ├─ .github/workflows/ci.yml         # CI: ruff + pyright on push/PR
  ├─ AGENTS.md                        # AI contributor quick guide
  ├─ CHANGELOG.md                     # Change history
  ├─ DEVELOPER_HANDBOOK.md            # Detailed technical documentation
  ├─ LOCAL_DEVELOPMENT.md             # Local dev setup guide
  ├─ PLAN.md                          # Horizontal splitting plan
  ├─ PROJECT_STRUCTURE.md             # This file
  ├─ README.md                        # Primary public README
  └─ LICENSE                          # AGPL-3.0
```

## Module Responsibilities

| Module | Role | Lines | Dependencies |
|---|---|---|---|
| `health_monitor.py` | Main entry, UI orchestration, event loop | ~9,800 | All other modules |
| `monitor_analyzer.py` | Health/mana HSV analysis, trigger logic | 349 | cv2, numpy |
| `capture_utils.py` | Screenshot capture, mss singleton | 72 | mss, PIL, numpy |
| `image_utils.py` | Image drawing, resizing, preview utilities | 203 | PIL |
| `inventory_utils.py` | Inventory slot analysis, item detection | 95 | numpy |
| `config_manager.py` | JSON config load/save with backup | 208 | none |
| `custom_dialogs.py` | Modal dialogs with dynamic sizing | 215 | tkinter |
| `language_system.py` | Bilingual string lookup | 144 | JSON |
| `skill_timer.py` | Skill cooldown timer module | 432 | tkinter |
| `utils.py` | Emergency cleanup, F12 handler, Tooltip | 166 | keyboard, psutil |

## Canonical Source Rules

- Edit runtime code in `src/`.
- Treat `src/` as the single source of truth.
- Do not assume runtime-generated files under `src/` are stable source files.

## Important Runtime Files

- `src/health_monitor.py` remains the main application file and orchestration layer.
- All other `src/*.py` are active modularized components used by the main app.
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
- `scripts/requirements.txt`: Python dependency manifest
- `scripts/auto_click.ahk`: AutoHotkey auto-clicker source

## Tools

- `tools/build.py` is the packaging source of truth.
- `tools/GameTools_HealthMonitor.ico` is the application icon.

## Documentation Notes

- `README.md` exists (bilingual Traditional Chinese + English).
- `README_EN.md` is not currently present and should not be referenced as if it already exists.
- `docs/` includes usage guides, architecture notes, and release notes.
- `PLAN.md` documents the horizontal splitting history and outcomes.
- `AGENTS.md` provides AI contributor workflow guidance (ruff, pyright, commitizen).

## CI

- `.github/workflows/ci.yml` runs `ruff check src/` and `pyright src/health_monitor.py` on every push/PR to `master`.

## Version Notes

- Single source of truth: `src/_version.py` (`__version__`)
- `health_monitor.py` imports as `CURRENT_VERSION = f"v{__version__}"`
- `build.py` imports as `APP_VERSION = __version__`
- Commitizen manages version via `src/_version.py:__version__`

## Packaging Notes

- Packaging is driven solely by `tools/build.py` sourcing from `src/`.
- Expected packaged assets include:
  - `GameTools_HealthMonitor.exe`
  - `auto_click.exe`
  - `language_packs.json`
  - `使用說明.md`
  - `啟動工具.bat`
  - `README.txt`

## Code Quality

| Metric | Before | After |
|---|---|---|
| `health_monitor.py` lines | ~10,500 | ~9,800 |
| Module count | 6 | 10 |
| Ruff errors | 100 | 11 (all C901) |
| Bare `except:` | 39 | 0 |
| F821 undefined names | 5 | 0 |
| CI | None | ruff + pyright on push/PR |

## Current Status

- Horizontal splitting complete: 4 new modules extracted (719 lines total).
- All F821, E722, E402 ruff errors resolved.
- CI pipeline active with ruff lint + pyright type check.
- Remaining 11 C901 warnings are pre-existing complex functions (refactor candidates).
