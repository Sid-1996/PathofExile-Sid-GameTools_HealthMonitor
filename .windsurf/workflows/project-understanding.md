---
description: Quick understanding guide for Path of Exile automation tool project
---

# Project Understanding - Path of Exile Automation Tool

## Project Overview

Windows automation tool for Path of Exile with these core features:

- **Health/Mana Monitor**: Real-time monitoring with automatic potion triggering
- **Skill Combo System**: Customizable skill sequences with delays
- **Inventory Management**: One-click inventory clearing and item pickup
- **Global Hotkeys**: F3 (clear), F5 (hideout), F6 (pickup), F9 (pause), F10 (monitor toggle), F12 (close)
- **Auto-click Integration**: Ctrl+left-click toggle

**Tech Stack:**

- Python 3.10+ with Tkinter GUI
- OpenCV + NumPy for image processing
- keyboard library for global hotkeys
- PyAutoGUI for input simulation
- PyInstaller for EXE packaging

## Canonical Structure

```text
Python POE/
├── src/                              # CANONICAL SOURCE (edit here)
│   ├── health_monitor.py              # Main application (10,554 lines)
│   ├── language_packs.json            # Bilingual UI strings
│   ├── health_monitor_config.json     # User config (auto-generated)
│   └── screenshots/                   # Region selection screenshots (auto-generated)
├── src for DEVELOPER/                # COMPATIBILITY LAYER (legacy fallback)
│   └── [mirrored files from src/]
├── scripts/                           # One-click workflows
│   ├── install_dependencies.bat       # pip install -r requirements.txt
│   ├── run_monitor.bat                # Run from source
│   ├── build_exe.bat                  # Build EXE (copies src→src for DEVELOPER first)
│   └── test_built_exe.bat             # Test built EXE
├── tools/                             # Build pipeline
│   ├── build.py                       # PyInstaller packaging (APP_VERSION = "1.0.7")
│   └── GameTools_HealthMonitor.ico     # Application icon
├── docs/                              # Documentation
│   ├── 使用指南.md, 使用說明.md        # User guides (Chinese)
│   ├── 運作原理.md                     # Technical explanation
│   └── RELEASE_NOTES.md               # Version history
├── AGENTS.md                          # AI contributor quick guide
├── DEVELOPER_HANDBOOK.md              # Detailed technical documentation (908 lines)
└── PROJECT_STRUCTURE.md               # Directory overview
```

**CRITICAL RULE**: Always edit files in `src/`. The `src for DEVELOPER/` directory exists only for backward compatibility with existing build scripts. Never edit it directly.

## Developer Habits & Conventions

### Version Management

- **Single Source of Truth**: `APP_VERSION` in `tools/build.py` (currently "1.0.7")
- **Sync Required**: When updating version, also update:

  - `src/health_monitor.py` line 85: `CURRENT_VERSION = "v1.0.7"`
  - README.md badges and version references
  - DEVELOPER_HANDBOOK.md version history

### Code Organization

- **Monolithic Design**: Single 10,554-line file (`health_monitor.py`) with two main classes:

  - `CustomMessageBox` (line 156): Custom dialog wrapper
  - `HealthMonitor` (line 338): Main application class

- **Method Categories**: Organized by functionality (GUI, monitoring, hotkeys, combo, config, version)
- **Naming**: snake_case for methods/variables, PascalCase for classes

### Configuration Management

- **JSON-based**: All settings in `health_monitor_config.json`
- **Atomic Saves**: Uses temp file pattern (`.tmp`) then atomic replace
- **Default Values**: Config validation with fallback to defaults
- **User-Generated**: Never commit `health_monitor_config.json` or `screenshots/`

### Threading Pattern

- **Monitoring Thread**: Health/mana monitoring in separate thread
- **Combo Thread**: Skill combo system in separate thread
- **Thread Safety**: Uses `functools.partial` for hotkey callbacks to avoid closure issues
- **Cleanup**: Global `emergency_cleanup()` with `atexit.register()`

### Language Support

- **Bilingual UI**: Chinese (default) + English
- **Language Packs**: `language_packs.json` with key-value translations
- **Dynamic Switching**: Runtime language change via UI dropdown
- **Documentation**: Keep both `README.md` (Chinese) and `README_EN.md` (English) in sync

### Error Handling

- **Graceful Degradation**: OpenCV optional (OPENCV_AVAILABLE flag)
- **Try-Except Blocks**: Extensive error handling around external operations
- **User Feedback**: Status messages in GUI for all operations
- **Emergency Exit**: F12 global handler for force-close

## Critical Workflows

### Development Workflow

#### 1. Install Dependencies

```batch
scripts\install_dependencies.bat
```

Installs: PyInstaller, opencv-python, numpy, pillow, mss, keyboard, pygetwindow, pyautogui, psutil, requests

#### 2. Run from Source

```batch
scripts\run_monitor.bat
```

Runs `src/health_monitor.py` directly with Python

#### 3. Make Changes

- Edit files in `src/` directory only
- Test with `scripts/run_monitor.bat`
- Update version in both `tools/build.py` and `src/health_monitor.py`

#### 4. Build EXE

```batch
scripts\build_exe.bat
```

Process:

1. Copies `src/` files to `src for DEVELOPER/` (for compatibility)
2. Clears PyInstaller cache if locked
3. Runs `tools/build.py` (PyInstaller with extensive hidden-imports)
4. Creates package in `dist/GameTools_Package/`
5. Generates ZIP with timestamp

#### 5. Test Built EXE

```batch
scripts\test_built_exe.bat
```

Launches the built EXE for smoke testing

### Build System Details

**tools/build.py Key Points:**

- Prefers `src/` but falls back to `src for DEVELOPER/`
- Extensive PyInstaller flags for all dependencies (PIL, OpenCV, Tkinter, etc.)
- Adds binary dependencies manually (DLLs, .pyd files)
- Creates ZIP package with specific file set
- Estimated build time: 9-17 minutes

**Final Package Contents (REQUIRED):**

- `GameTools_HealthMonitor.exe` - Main application
- `auto_click.exe` - AutoHotkey auto-click tool
- `language_packs.json` - UI translations
- `使用說明.md` - Chinese user guide
- `README.txt` - Quick start guide
- `啟動工具.bat` - Launcher script

**EXCLUDE from Package:**

- `screenshots/` - User-generated region screenshots
- `health_monitor_config.json` - User configuration
- Any temporary or test files

## Common Pitfalls

### PyInstaller Cache Lock

**Symptom**: `WinError 5` during build

**Solution**: Clear `build/GameTools_HealthMonitor` directory and rebuild

```batch
rmdir /s /q "build\GameTools_HealthMonitor"
scripts\build_exe.bat
```

### Dual Source Desync

**Symptom**: Changes in `src/` not reflected in build

**Cause**: `src for DEVELOPER/` not updated

**Solution**: The build script handles this, but if manually building, copy files:

```batch
copy /Y "src\health_monitor.py" "src for DEVELOPER\health_monitor.py"
copy /Y "src\language_packs.json" "src for DEVELOPER\language_packs.json"
```

### Version Inconsistency

**Symptom**: Version mismatch between files

**Check**: Ensure `APP_VERSION` in `tools/build.py` matches `CURRENT_VERSION` in `src/health_monitor.py`

**Format**: `tools/build.py` uses "1.0.7", `health_monitor.py` uses "v1.0.7"

### OpenCV Import Failure

**Symptom**: "OpenCV不可用" warning, limited functionality

**Cause**: Missing opencv-python dependency

**Solution**: Run `scripts/install_dependencies.bat`

### Global Hotkeys Not Working

**Symptom**: Hotkeys unresponsive

**Causes:**

1. Global pause active (press F9 to toggle)
2. Keyboard library not installed
3. Conflicting hotkeys in other apps
4. Insufficient permissions

### Bilingual Doc Out of Sync

**Symptom**: Chinese and English docs have different content

**Solution**: Always update both `README.md` and `README_EN.md` when making public-facing changes

## Quick Reference

### File Locations

- **Main App**: `src/health_monitor.py` (10,554 lines)
- **Build Script**: `tools/build.py` (APP_VERSION line 14)
- **Language Packs**: `src/language_packs.json`
- **User Config**: `src/health_monitor_config.json` (auto-generated, don't commit)
- **AI Guide**: `AGENTS.md` (quick reference)
- **Tech Docs**: `DEVELOPER_HANDBOOK.md` (detailed)

### Key Functions (health_monitor.py)

- `HealthMonitor.__init__()` - Application initialization (line 338)
- `HealthMonitor.monitor_health()` - Main monitoring loop
- `HealthMonitor.execute_combo()` - Skill combo execution
- `HealthMonitor.setup_hotkeys()` - Global hotkey registration
- `emergency_cleanup()` - Global cleanup handler (line 33)
- `get_app_dir()` - Path resolution for dev/exe (line 62)

### Hotkey Bindings

- **F3**: One-click inventory clear
- **F5**: Return to hideout
- **F6**: Item pickup (5 coordinates)
- **F9**: Global pause/resume all hotkeys
- **F10**: Toggle health/mana monitoring
- **F12**: Emergency close application
- **Ctrl+Left Click**: Toggle auto-click

### Configuration Structure

```json
{
  "window_title": "Path of Exile 2",
  "region": [x, y, width, height],           // Health bar region
  "mana_region": [x, y, width, height],      // Mana bar region
  "settings": [                              // Trigger thresholds
    {"type": "health", "percent": 60, "key": "1", "cooldown": 1500},
    {"type": "mana", "percent": 10, "key": "2", "cooldown": 1500}
  ],
  "inventory_region": [x, y, width, height], // Inventory UI region
  "combo_sets": [                            // Skill combos
    {"trigger_key": "Q", "combo_keys": ["Q", "W", "E"], "delays": [500, 500, 500]}
  ]
}
```

### Testing Checklist Before Release

- [ ] No secrets/tokens/private keys in code
- [ ] No accidental mirror directories
- [ ] README versions/links match current release
- [ ] Build completes successfully
- [ ] Built EXE launches and functions
- [ ] Bilingual docs are in sync
- [ ] Version numbers consistent across files

## Architecture Patterns

### Image Processing Pipeline

1. **Screen Capture**: MSS library captures specified region
2. **Preprocessing**: NumPy array conversion, noise reduction
3. **Color Detection**: HSV color space analysis (18-point sampling)
4. **Threshold Comparison**: Pixel ratio against health_threshold
5. **Trigger Decision**: Cooldown-based action triggering

### Threading Model

- **Main Thread**: Tkinter GUI event loop
- **Monitor Thread**: Health/mana analysis (100ms interval)
- **Combo Thread**: Skill sequence execution with delays
- **Cleanup Thread**: Emergency resource cleanup

### State Management

- **Global Variables**: `_app_instance` for F12 emergency handler
- **Instance State**: All settings in HealthMonitor instance attributes
- **Persistence**: JSON config file with atomic saves
- **Runtime State**: Threading flags (monitoring_active, combo_running, global_pause)

## Future Refactor Notes

From AGENTS.md:

- `src for DEVELOPER/` can be removed only after all packaging and release scripts stop depending on it
- Current build script still copies from `src/` to `src for DEVELOPER/` for compatibility

Potential improvements:

- Split monolithic `health_monitor.py` into modules
- Extract configuration management to separate class
- Separate UI logic from business logic
- Add unit tests for core algorithms
- Migrate from dual source to single source structure
