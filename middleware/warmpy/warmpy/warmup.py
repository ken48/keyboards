from __future__ import annotations

import importlib
import json
import logging
import time
from pathlib import Path


def _find_warmup_json() -> Path | None:
    # Prefer bundle Resources (py2app)
    try:
        from Cocoa import NSBundle  # type: ignore

        p = NSBundle.mainBundle().pathForResource_ofType_("warmup", "json")
        if p:
            path = Path(str(p))
            if path.exists():
                return path
    except Exception:
        pass

    # Fallback for dev runs
    candidates = [
        Path(__file__).resolve().parent / ".." / "Resources" / "warmup.json",
        Path(__file__).resolve().parent / ".." / ".." / "Resources" / "warmup.json",
    ]
    for c in candidates:
        c = c.resolve()
        if c.exists():
            return c
    return None


def warmup() -> None:
    meta_path = _find_warmup_json()
    if not meta_path:
        logging.info("WARMUP skip (metadata not found)")
        return

    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
        mods = data.get("warmup") or data.get("imports") or []
        if isinstance(mods, str):
            mods = [mods]
        if not isinstance(mods, list):
            raise RuntimeError("warmup/imports must be a list")
        mods = [m.strip() for m in mods if isinstance(m, str) and m.strip()]
    except Exception:
        logging.exception("WARMUP failed to read metadata path=%s", meta_path)
        return

    if not mods:
        logging.info("WARMUP skip (empty) path=%s", meta_path)
        return

    logging.info("WARMUP start n=%d path=%s", len(mods), meta_path)
    for name in mods:
        t0 = time.perf_counter()
        ok = True
        err = None
        try:
            importlib.import_module(name)
        except Exception as e:
            ok = False
            err = repr(e)
            logging.exception("WARMUP import fail module=%s", name)
        ms = int((time.perf_counter() - t0) * 1000)
        logging.info("WARMUP module=%s ok=%s ms=%s err=%s", name, ok, ms, err)
