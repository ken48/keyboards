from __future__ import annotations

from pathlib import Path
import yaml

CONFIG_DIR = Path.home() / ".warmpy"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Hardcoded locations (contract)
LOG_FILE = CONFIG_DIR / "warmpy.log"
SOCKET_FILE = CONFIG_DIR / "warmpy.sock"
PID_FILE = CONFIG_DIR / "runner.pid"

DEFAULT = {
    "plugins_dir": str(CONFIG_DIR / "plugins"),
}

def load_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(yaml.safe_dump(DEFAULT), encoding="utf-8")
        return dict(DEFAULT)

    data = yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")) or {}
    cfg = {**DEFAULT, **data}
    # keep hardcoded paths available for convenience
    cfg["log_file"] = str(LOG_FILE)
    cfg["socket_path"] = str(SOCKET_FILE)
    return cfg
