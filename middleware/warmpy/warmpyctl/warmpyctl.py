#!/usr/bin/env python3
import socket
import sys
from pathlib import Path

SOCKET_PATH = str(Path.home() / ".warmpy" / "warmpy.sock")

def main():
    if len(sys.argv) < 2:
        print("Usage: warmpyctl <script.py> [args...]")
        sys.exit(1)

    plugin = sys.argv[1]
    args = sys.argv[2:]
    payload = "\0".join([plugin] + args).encode("utf-8")

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.connect(SOCKET_PATH)
    s.sendall(payload)
    s.close()

if __name__ == "__main__":
    main()
