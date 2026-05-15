# Safe Modularization SOP

> Use this workflow for future modularization work on `src/health_monitor.py`.
>
> This document assumes the project is currently functional and that the goal is to split code safely without regressing runtime behavior.

## Current Baseline

- The latest modularization recovery pass is functionally restored.
- The current codebase already uses these extracted helper modules:
  - `src/config_manager.py`
  - `src/language_system.py`
  - `src/utils.py`
  - `src/custom_dialogs.py`
- `src/health_monitor.py` is still the main integration layer.

## Primary Rule

Do not treat modularization as a bulk file-moving exercise.

A safe modularization pass should:

1. isolate one coherent responsibility
2. extract only that responsibility
3. verify compile/import/runtime behavior immediately
4. stop if shutdown behavior regresses

## Source-of-Truth Rule

- Edit `src/`.
- Use `src for DEVELOPER/` only as a compatibility reference when necessary.
- Do not use `src for DEVELOPER/` as the default source for new refactors.

## What Is Safe to Extract

Good candidates:

- pure helper functions
- config transformation helpers
- language/formatting helpers
- isolated dialog logic
- self-contained utility functions

Higher-risk candidates:

- startup ordering
- config-to-UI application
- monitoring thread logic
- combo lifecycle logic
- shutdown flow
- Tk callback scheduling
- anything that mixes worker threads with UI access

## Pre-Change Checkpoint

Before extracting anything:

```powershell
Set-Location "C:\Code play first\Python POE"
python -m py_compile src/health_monitor.py
python src/health_monitor.py
```

If the current baseline is already broken, stop and use `modularization-recovery.md` instead.

## Safe Extraction Sequence

### Phase A - Identify One Slice

Pick one narrow target only.

Examples:

- a cluster of config helpers
- a language/translation wrapper
- a custom-dialog block
- path/cleanup helpers

Do not extract two unrelated areas in the same pass.

### Phase B - Compare Dependencies First

Before moving code, inspect:

- imports
- `self` usage
- Tk widget access
- thread access
- config assumptions

If the target relies heavily on live widget state, it may not be a safe extraction candidate yet.

### Phase C - Create the Module

Create or extend one module under `src/`.

General rule:

- move code with the fewest possible edits first
- keep imports explicit
- avoid hidden back-references to `HealthMonitor`

### Phase D - Compile the New Module

```powershell
python -m py_compile src\<module_name>.py
```

Do this before wiring the new import into `health_monitor.py`.

### Phase E - Rewire Imports in `health_monitor.py`

Only after the extracted module compiles:

```python
from <module_name> import ...
```

Keep the integration diff small. Avoid cleanup refactors in the same step unless they are required for correctness.

### Phase F - Re-run Main Compile

```powershell
python -m py_compile src/health_monitor.py
```

### Phase G - Launch Test

```powershell
python src/health_monitor.py
```

If launch fails, stop and fix the exact failure before continuing.

## Required Regression Checks

Do not stop at successful launch.

### Minimum Checks for Any Modularization Pass

- `python -m py_compile src/health_monitor.py`
- launch the app
- exercise the directly affected feature

### Additional Checks for Lifecycle-Sensitive Changes

If the extraction touched startup, shutdown, worker threads, or UI scheduling, also verify:

- normal open -> operate -> close cycle
- no stale `after(...)` callback errors
- no `invalid command name`
- no `RuntimeError: main thread is not in main loop`
- no worker thread touching destroyed Tk widgets

This is mandatory. The recent recovery proved that lifecycle regressions can appear even when launch and smoke tests look fine.

## Git Discipline

Do not use `git add -A` by default during modularization in a mixed worktree.

Preferred behavior:

- stage only request-scoped files
- keep generated config/screenshots out of the commit unless explicitly intended
- commit small, reversible slices

## When to Stop and Reassess

Stop the modularization pass if:

- a compile error appears outside the target slice
- startup ordering changes unexpectedly
- config starts being read before initialization
- worker threads begin touching Tk after close
- you find yourself wanting to overwrite `src/` from `src for DEVELOPER/`

At that point, either narrow the scope further or switch to recovery mode.

## Recommended Commit Shape

Good modularization commits look like:

- one responsibility extracted
- one integration point updated
- one validation round completed

Bad modularization commits look like:

- multiple unrelated slices moved at once
- extraction plus broad cleanup plus rename churn
- lifecycle-sensitive code changed without close regression testing

## Suggested Future Extraction Order

Safer next candidates tend to be:

1. additional pure utility helpers
2. config transformation helpers
3. non-widget formatting or display helpers
4. isolated feature-specific helper blocks

Leave these for later unless there is a strong reason:

- shutdown logic
- thread lifecycle code
- hotkey orchestration
- monitor loop internals tightly coupled to UI state

## Windows Console Note

When touching logging or `print(...)` output, remember that this project runs in Windows environments where cp950/console encoding issues can matter.

Avoid introducing emoji or fragile non-ASCII console output into critical debug paths unless there is a clear reason and the environment is known to support it.
