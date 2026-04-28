# Compatibility Directory Note

`src for DEVELOPER/` is kept as a compatibility layer for older build and release workflows.

Current canonical source files are in `src/`:

- `src/health_monitor.py`
- `src/language_packs.json`

If a script still reads from this directory, it should be updated to prefer `src/` first and fall back to this directory only when needed.
