#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


SOCK = os.path.expanduser("~/.warmpy/warmpy.sock")


def _normalize_plugin(arg: str) -> str:
    # Contract: daemon runs a .py file from plugins_dir.
    # We allow passing either "name" or "name.py"; keep filename.
    p = Path(arg).name
    if not p.endswith(".py"):
        p = f"{p}.py"
    return p


def main():
    if len(sys.argv) < 2:
        print("usage: warmpyctl <plugin[.py]> [key=value ...]")
        sys.exit(2)

    plugin = _normalize_plugin(sys.argv[1])

    # No parsing/heuristics: pass raw argv to the script.
    req = {"plugin": plugin, "args": sys.argv[2:]}

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCK)
    s.sendall(json.dumps(req).encode("utf-8"))
    try:
        s.shutdown(socket.SHUT_WR)
    except Exception:
        pass
    s.close()


if __name__ == "__main__":
    main()
