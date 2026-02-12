# WarmPy v5 (all agreements)

## Build (use Python 3.11 for py2app)
```bash
WARMPY_PYTHON=/opt/homebrew/opt/python@3.11/bin/python3.11 ./build.sh --plugins-dir /abs/path/to/plugins
```

## Runtime contract
- plugins folder is NOT bundled; it is external and can be edited freely.
- dependencies are the user's responsibility; WarmPy is a warmed interpreter.
- if any plugin file changes, WarmPy shows warning icon and warning marks; restart required.

## IPC
- socket: ~/.warmpy/warmpy.sock
- ctl: python3 warmpyctl/warmpyctl.py auto_layout_fixer.py [args...]


### Busy policy
If a plugin is currently running, WarmPy **drops** incoming commands (no queue).
Log: `DROP busy ...`

## Build deps metadata (in your plugins/scripts folder)

Place a `warmpy_build_deps.yaml` next to your scripts directory (the same directory you pass to `build.sh`).

Example:

```yaml
# Extra pip deps to install into the build venv
pip:
  - pillow
  - pyyaml
  - pyobjc-framework-Quartz

# Extra modules to force-include into the py2app bundle (modulegraph misses dynamic imports)
includes:
  - Quartz
  - AppKit
  - yaml
  - PIL

# Optional: hidden imports (submodules) if needed
hidden_imports: []

# Modules to import at app startup (warmup to avoid first-hotkey latency)
warmup:
  - Quartz
  - AppKit
  - yaml
  - PIL
```

At build time, `build.sh` will:
- install `pip` deps
- write py2app `includes` from `includes + hidden_imports + warmup`
- embed `assets/warmpy_warmup.json` into the app for runtime warmup


## Warmup metadata

Place `warmpy_build_deps.yaml` in your scripts folder.

Minimal (legacy-compatible):

```yaml
pip:
  - pyobjc
  - pyobjc-framework-Quartz

# legacy key (treated as warmup list):
imports:
  - Quartz
  - AppKit
```

Optional extra warmup (stdlib / infra modules):

```yaml
warmup_extra (merged into warmup at build time):
  - runpy
  - argparse
```

`imports` and `warmup` are treated equivalently for warmup.


## Minimal runner mode

This build is a TCC-friendly .app wrapper around Python:

- Warmup imports are defined in `warmpy_build_deps.yaml` (`imports:` + optional `warmup_extra:`).
- At runtime, `warmpyctl` sends an absolute/relative path to a `.py` script and args.
- The app executes the script as `__main__` (like running Python directly), but inside the `.app` for TCC.

No pid file. No runtime config. No plugins directory constraint.
