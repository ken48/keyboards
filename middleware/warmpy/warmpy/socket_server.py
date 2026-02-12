import atexit
import logging
import socket
import threading

from .paths import WARMPY_DIR, SOCKET_PATH


class SocketServer:
    def __init__(self, worker):
        self.worker = worker
        self._stop = threading.Event()
        self._listen_t = threading.Thread(
            target=self._listen_loop, name="warmpy-sock-listen", daemon=True
        )

    def start(self):
        WARMPY_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if SOCKET_PATH.exists():
                SOCKET_PATH.unlink()
        except Exception:
            logging.exception("SOCKET unlink failed path=%s", SOCKET_PATH)

        atexit.register(self._cleanup)

        self._listen_t.start()
        logging.info("SOCKET started path=%s", SOCKET_PATH)

    def _cleanup(self):
        try:
            if SOCKET_PATH.exists():
                SOCKET_PATH.unlink()
        except Exception:
            pass

    def _listen_loop(self):
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.bind(str(SOCKET_PATH))
            s.listen(5)
            while not self._stop.is_set():
                try:
                    conn, _ = s.accept()
                except Exception:
                    continue
                try:
                    data = conn.recv(1024 * 1024)
                    if not data:
                        continue
                    parts = data.decode("utf-8", errors="replace").split("\0")
                    script = parts[0].strip()
                    args = [p for p in parts[1:] if p != ""]
                    if script:
                        self.worker.run_script(script, args)
                except Exception:
                    logging.exception("SOCKET handle failed")
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        finally:
            try:
                s.close()
            except Exception:
                pass
