from __future__ import annotations

import os
import sys
from pathlib import Path

from warmpy.config import CONFIG_DIR, LOG_FILE, SOCKET_FILE, load_config


def init_env():
    # Predictable unicode/text behaviour when running as a GUI app.
    # Keep this minimal but effective (mirrors what worked in older TextOps builds).
    os.environ.setdefault("PYTHONUTF8", "1")
    os.environ.setdefault("LC_ALL", "en_US.UTF-8")
    os.environ.setdefault("LANG", "en_US.UTF-8")
    os.environ.setdefault("LC_CTYPE", "en_US.UTF-8")

    cfg = load_config()

    plugins_dir = Path(cfg["plugins_dir"]).expanduser()
    plugins_dir.mkdir(parents=True, exist_ok=True)

    # Ensure plugin modules are importable
    p = str(plugins_dir)
    if p not in sys.path:
        sys.path.insert(0, p)

    # Expose hardcoded paths (even though config.yaml stores only plugins_dir)
    cfg["log_file"] = str(LOG_FILE)
    cfg["socket_path"] = str(SOCKET_FILE)

    # Ensure base dir exists and is private.
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_DIR.chmod(0o700)
    except Exception:
        pass

    return cfg, plugins_dir
