from __future__ import annotations

import json
from pathlib import Path

from setuptools import setup

APP = ["main.py"]

# Extra modules to force-include in py2app are provided by build.sh as a merged
# JSON file in .build/warmpy_build_deps.json. This is part of the build
# contract and intentionally contains Python *module* names (not pip package
# names).
extra_includes: list[str] = []
deps_path = Path(".build") / "warmpy_build_deps.json"
if deps_path.exists():
    try:
        data = json.loads(deps_path.read_text("utf-8"))
        extra_includes = list(data.get("import") or [])
    except Exception:
        # If the file is broken, fail early during packaging.
        raise

OPTIONS = {
    "argv_emulation": False,
    "packages": ["warmpy"],
    # Only what WarmPy itself needs. Plugin modules to include are provided via build_deps.
    "includes": ["objc", "Foundation", "AppKit", *extra_includes],
    "plist": {
        "LSUIElement": True,  # menu bar app, без Dock
    },
    "iconfile": "assets/warmpy.icns",
    # Keep build artifacts in one place.
    "dist_dir": ".build/dist",
    "bdist_base": ".build/build",
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    # py2app is installed by build.sh inside the venv.
)