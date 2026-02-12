import logging
import os
import runpy
import sys
import threading
import time
from pathlib import Path


class Worker:
    """Minimal single-process runner (TCC-friendly .app wrapper).

    - No engine subprocess.
    - No queue: if busy -> drop.
    - Scripts are plain Python files; warmpy executes them as __main__.
    - Warmup happens via metadata (see warmpy.warmup).
    - Accepts an absolute/relative path to a .py file.
    """

    def __init__(self):
        self._busy_lock = threading.Lock()
        self._busy = False

    def start(self):
        logging.info("WORKER start mode=inproc-runner pid=%s", os.getpid())

    def is_busy(self) -> bool:
        with self._busy_lock:
            return self._busy

    def _set_busy(self, val: bool):
        with self._busy_lock:
            self._busy = val

    def run_script(self, script_path: str, args=None) -> bool:
        args = args or []

        if self.is_busy():
            logging.warning("DROP busy script=%s args=%s", script_path, args)
            return False

        path = Path(script_path).expanduser().resolve()

        if path.suffix.lower() != ".py":
            logging.error("REJECT not a .py file: %s", path)
            return False

        if not path.exists() or not path.is_file():
            logging.error("MISSING script=%s", path)
            return False

        self._set_busy(True)
        logging.info("ACCEPT script=%s args=%s", path, args)

        def _job():
            t0 = time.perf_counter()
            ok = True
            err = None
            old_argv = sys.argv
            # Temporarily add the script directory to sys.path for sibling imports
            script_dir = str(path.parent)
            added = False
            try:
                if script_dir and script_dir not in sys.path:
                    sys.path.insert(0, script_dir)
                    added = True

                sys.argv = [str(path), *list(args)]
                runpy.run_path(str(path), run_name="__main__")
            except Exception as e:
                ok = False
                err = repr(e)
                logging.exception("FAIL script=%s", path)
            finally:
                sys.argv = old_argv
                if added:
                    try:
                        sys.path.remove(script_dir)
                    except ValueError:
                        pass
                ms = int((time.perf_counter() - t0) * 1000)
                logging.info("DONE script=%s ok=%s ms=%s err=%s", path, ok, ms, err)
                self._set_busy(False)

        threading.Thread(target=_job, name=f"script-{path.name}", daemon=True).start()
        return True
