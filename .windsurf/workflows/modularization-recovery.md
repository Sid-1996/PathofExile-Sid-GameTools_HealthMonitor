# Modularization Recovery Reference

> This document is now a recovery reference, not an instruction that the project is currently broken.
>
> Use it only if a future modularization pass breaks `src/health_monitor.py` again.

## Current Status

- The latest modularization recovery pass is functionally restored.
- The latest verified smoke-test round passed.
- `git push` is still locked pending final review.

## What This Recovery Actually Fixed

The latest recovery pass addressed these concrete problems:

- `load_config()` structure damage, including an `IndentationError`
- `self.config` initialization order before UI access
- shutdown lifecycle issues involving:
  - stale Tk `after(...)` callbacks
  - `silent_version_check`
  - usage-time callback cleanup
  - background thread interaction with Tk during close
- cp950 console failures from emoji-bearing `print(...)`

Any future recovery should assume these areas are fragile.

## Recovery Entry Rule

Do not start with recovery just because the file looks large or messy.

Start recovery only if one of these is true:

- `python src/health_monitor.py` fails
- `python -m py_compile src/health_monitor.py` fails
- startup works but shutdown produces callback/thread/Tk errors
- a modularization change introduced clear runtime regressions

## Step 0 - Capture the Real Failure First

Use Windows/PowerShell-friendly commands.

```powershell
Set-Location "C:\Code play first\Python POE"
python -m py_compile src/health_monitor.py
python src/health_monitor.py
```

If launch output is noisy, capture it explicitly:

```powershell
python src/health_monitor.py *> recovery-launch.log
```

Do not guess based on code shape alone. Start from the actual failing path.

## Step 1 - Compare `src/` Against the Compatibility Copy

Only compare when needed. Do not assume the old file is more correct.

```powershell
Get-Content src\health_monitor.py -Head 120
Get-Content "src for DEVELOPER\health_monitor.py" -Head 120
```

Useful comparison questions:

- Did an import move but the source file not follow?
- Did runtime state initialization move after a UI access?
- Did worker-thread or callback cleanup regress?
- Did the new code add a bug that the old code did not have?

## Step 2 - Validate Modular Files Independently

If the helper modules are involved, compile them directly:

```powershell
python -m py_compile src\config_manager.py
python -m py_compile src\language_system.py
python -m py_compile src\utils.py
python -m py_compile src\custom_dialogs.py
```

If one helper fails, fix the helper instead of guessing at the main file.

## Step 3 - Validate Imports Explicitly

```powershell
python -c "import sys; sys.path.insert(0, 'src'); from config_manager import *; print('config_manager OK')"
python -c "import sys; sys.path.insert(0, 'src'); from language_system import *; print('language_system OK')"
python -c "import sys; sys.path.insert(0, 'src'); from utils import *; print('utils OK')"
python -c "import sys; sys.path.insert(0, 'src'); from custom_dialogs import *; print('custom_dialogs OK')"
```

## Step 4 - Choose the Recovery Direction

Use the narrowest valid fix.

### Option A - Local Repair in `src/`

Use this when:

- the failure is clearly local
- the modularized version is mostly correct
- rollback would throw away known-good fixes

Typical examples:

- bad indentation
- broken initialization order
- stale callback cleanup
- thread/Tk boundary issues

### Option B - Reconstruct from `src for DEVELOPER/`

Use this only when:

- the `src/` version is unrecoverably damaged
- the compatibility copy is demonstrably closer to correct behavior
- you are willing to re-apply newer fixes manually afterward

Important warning:

- `src for DEVELOPER/` is not guaranteed to include the latest lifecycle and recovery fixes
- using it as a blind overwrite source can reintroduce already-fixed bugs

## Step 5 - High-Risk Fallback

Direct overwrite from `src for DEVELOPER/` is a last resort.

```powershell
Copy-Item "src for DEVELOPER\health_monitor.py" "src\health_monitor.py" -Force
```

Only do this when you have explicitly decided to abandon the current `src/` state.

If you do use it, immediately re-check:

- `load_config()`
- config/UI initialization order
- close lifecycle
- callback cleanup
- worker-thread Tk safety

## Step 6 - Recovery Validation

Do not stop after compile success.

Minimum checks:

```powershell
python -m py_compile src/health_monitor.py
python src/health_monitor.py
```

If the changed area touches lifecycle, also run:

- normal open -> operate -> close cycle
- verify there is no:
  - `invalid command name`
  - `RuntimeError: main thread is not in main loop`
  - worker thread touching destroyed widgets

## Recovery Guardrails

- Do not edit `src for DEVELOPER/` as the primary fix target.
- Do not assume older code is safer than newer code.
- Do not jump to full rollback before isolating the actual failure.
- Do not treat package-asset issues such as missing `auto_click.exe` as proof that modularization is broken.
- Do not `git push` during recovery.

## Suggested Recovery Mindset

The safest default is:

1. capture the real error
2. fix the smallest broken path
3. re-test immediately
4. treat shutdown behavior as part of correctness, not a secondary concern
