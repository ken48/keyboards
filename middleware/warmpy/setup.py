from setuptools import setup
import json
from pathlib import Path

APP = ["main.py"]

extra_includes = []
p = Path(".build/extra_includes.json")
if p.exists():
    extra_includes = json.loads(p.read_text("utf-8"))

OPTIONS = {
    "iconfile": "assets/warmpy.icns",
    "argv_emulation": False,
    "packages": ["warmpy"],
    "resources": ["assets"],
    "iconfile": "assets/warmpy.icns",
    "plist": {"LSUIElement": True},
    "dist_dir": ".build/dist",
    "bdist_base": ".build/build",

    # isolation (not plugin-specific)
    "alias": False,
    "site_packages": False,
    "use_pythonpath": False,

    # plugin-specific (from deps file)
    "includes": extra_includes,
}

setup(
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)