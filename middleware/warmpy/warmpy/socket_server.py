from __future__ import annotations

import atexit
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
from pathlib import Path
from queue import Queue, Full

from warmpy.bootstrap import init_env
from warmpy.config import PID_FILE


_Q: "Queue[dict]" = Queue(maxsize=1)  # strict: at most one pending task
_CURRENT_PROC: subprocess.Popen | None = None


def _resolve_python_exe() -> str:
    # In py2app the main executable might not be the python binary.
    # Prefer sibling 'python' if present.
    exe = Path(sys.executable)
    cand = exe.with_name("python")
    if cand.exists():
        return str(cand)
    return str(exe)


def _kill_pid_group(pid: int) -> None:
    logging.info("KILL requested pid=%s", pid)
    try:
        os.killpg(pid, signal.SIGKILL)
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass


def _cleanup_stale_pidfile() -> None:
    if not PID_FILE.exists():
        return
    try:
        raw = PID_FILE.read_text(encoding="utf-8").strip()
        if raw:
            pid = int(raw)
            logging.info("Found stale pidfile pid=%s, killing process group", pid)
            _kill_pid_group(pid)
    except Exception:
        logging.exception("Failed to cleanup stale pidfile")
    finally:
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass


def _write_pidfile(pid: int) -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(pid), encoding="utf-8")
    logging.info("Wrote pidfile %s (pid=%s)", PID_FILE, pid)
    try:
        PID_FILE.chmod(0o600)
    except Exception:
        pass


def _remove_pidfile() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
        logging.info("Removed pidfile %s", PID_FILE)
    except Exception:
        pass


def _cleanup_current_proc() -> None:
    global _CURRENT_PROC
    p = _CURRENT_PROC
    if not p:
        _cleanup_stale_pidfile()
        return
    try:
        logging.info("Cleanup: killing running plugin process group pid=%s", p.pid)
        _kill_pid_group(p.pid)
    except Exception:
        pass
    finally:
        _CURRENT_PROC = None
        _remove_pidfile()


atexit.register(_cleanup_current_proc)


def _recv_all(conn: socket.socket, max_bytes: int = 1024 * 1024) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        part = conn.recv(64 * 1024)
        if not part:
            break
        chunks.append(part)
        total += len(part)
        if total > max_bytes:
            break
    return b"".join(chunks)


def _worker_loop(*, plugins_dir: Path) -> None:
    global _CURRENT_PROC
    python_exe = _resolve_python_exe()

    while True:
        req = _Q.get()
        try:
            plugin = req.get("plugin")
            args = req.get("args") or []
            if not plugin:
                logging.error("REQ missing plugin: %s", req)
                continue

            payload = {
                "plugins_dir": str(plugins_dir),
                "plugin": str(plugin),
                "args": args,
            }

            logging.info("RUN plugin=%s args=%s", plugin, args)
            proc = subprocess.Popen(
                [python_exe, "-m", "warmpy.plugin_runner"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,  # process group -> killpg on cleanup
            )
            _CURRENT_PROC = proc
            _write_pidfile(proc.pid)

            try:
                out, err = proc.communicate(json.dumps(payload))
            finally:
                # Always remove pidfile once the runner exits.
                _remove_pidfile()

            rc = proc.returncode
            if rc == 0:
                if out.strip():
                    logging.info("PLUGIN stdout:\n%s", out.rstrip())
                logging.info("DONE plugin=%s", plugin)
            else:
                logging.error("FAIL plugin=%s rc=%s", plugin, rc)
                if out.strip():
                    logging.error("PLUGIN stdout:\n%s", out.rstrip())
                if err.strip():
                    logging.error("PLUGIN stderr:\n%s", err.rstrip())

        except Exception:
            logging.exception("Worker loop error")
        finally:
            _CURRENT_PROC = None
            _Q.task_done()


def start_socket():
    cfg, plugins_dir = init_env()

    logging.basicConfig(
        filename=cfg["log_file"],
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

    logging.info("=== WarmPy started ===")
    logging.info("sys.executable=%s", sys.executable)
    logging.info("plugins_dir=%s", plugins_dir)

    # Clean up any orphan runner from a previous crash.
    _cleanup_stale_pidfile()

    sock_path = Path(cfg["socket_path"]).expanduser()
    sock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        sock_path.parent.chmod(0o700)
    except Exception:
        pass

    if sock_path.exists():
        sock_path.unlink()

    logging.info("Binding socket: %s", sock_path)

    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.bind(str(sock_path))
    try:
        sock_path.chmod(0o600)
    except Exception:
        pass
    s.listen(32)
    logging.info("Socket listening")

    # One worker, one task at a time.
    threading.Thread(target=_worker_loop, kwargs={"plugins_dir": plugins_dir}, daemon=True).start()
    logging.info("Worker thread started")

    def accept_loop():
        while True:
            conn, _ = s.accept()
            try:
                data = _recv_all(conn, 1024 * 1024)
                req = json.loads(data.decode("utf-8") or "{}")
                logging.info("REQ %s", req)

                try:
                    _Q.put(req, block=False)
                except Full:
                    logging.info("BUSY: skip request %s", req)
            except Exception:
                logging.exception("Accept loop error")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    threading.Thread(target=accept_loop, daemon=True).start()
    logging.info("Accept loop started")
