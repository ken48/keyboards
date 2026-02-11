from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path


def _resolve_script_path(plugins_dir: Path, plugin: str) -> Path:
    """Resolve requested plugin to an on-disk .py file.

    Contract (no heuristics):
      - plugin is a filename or stem within plugins_dir
      - we run it as a script (like old TextOps), not as a module import
    """
    p = Path(plugin)
    name = p.name
    if not name.endswith(".py"):
        name = f"{name}.py"
    return (plugins_dir / name).resolve()


def main() -> None:
    req = json.loads(sys.stdin.read() or "{}")
    plugins_dir = Path(req["plugins_dir"]).expanduser().resolve()
    script_path = _resolve_script_path(plugins_dir, req["plugin"])

    # Script-like execution environment
    os.chdir(str(plugins_dir))
    args = req.get("args") or []
    if not isinstance(args, list):
        # Be strict but defensive: allow old dict format as empty.
        args = []
    sys.argv = [str(script_path), *[str(x) for x in args]]
    sys.path.insert(0, str(plugins_dir))

    # Keep PyObjC happy if plugins touch Cocoa frameworks.
    try:
        import objc  # type: ignore

        with objc.autorelease_pool():
            runpy.run_path(str(script_path), run_name="__main__")
    except Exception:
        # Fallback: run without objc wrappers (also works when PyObjC isn't used)
        runpy.run_path(str(script_path), run_name="__main__")


if __name__ == "__main__":
    main()
