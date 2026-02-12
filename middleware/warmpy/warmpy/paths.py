from pathlib import Path

# Runtime directory for socket + logs (no config/pid)
WARMPY_DIR = Path.home() / ".warmpy"

SOCKET_PATH = WARMPY_DIR / "warmpy.sock"
LOG_FILE = WARMPY_DIR / "warmpy.log"
