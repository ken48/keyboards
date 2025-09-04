#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import subprocess
import sys
import time
import threading
from pathlib import Path
from typing import Dict, Tuple, Optional

from Quartz import (
    # event tap:
    CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
    CFRunLoopAddSource, CFRunLoopGetCurrent, CFRunLoopRun, kCFRunLoopCommonModes,
    kCGHIDEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
    kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput,
    # events:
    kCGEventKeyDown, kCGEventKeyUp,
    CGEventGetIntegerValueField, CGEventGetFlags,
    kCGKeyboardEventKeycode, kCGKeyboardEventAutorepeat,
    # flags (модификаторы):
    kCGEventFlagMaskShift, kCGEventFlagMaskControl,
    kCGEventFlagMaskAlternate, kCGEventFlagMaskCommand,
)

kCGSessionEventTap = 1  # ок

# ---------- утилиты ----------
def log(*a):
    print(*a, flush=True)

# ---------- keycodes ----------
VK: Dict[str, int] = {}
def _add(name: str, const_name: str):
    from Quartz import __dict__ as QD
    if const_name in QD:
        VK[name] = int(QD[const_name])

# ANSI буквы/цифры:
for ch, cname in {
    "a": "kVK_ANSI_A", "b": "kVK_ANSI_B", "c": "kVK_ANSI_C", "d": "kVK_ANSI_D", "e": "kVK_ANSI_E", "f": "kVK_ANSI_F",
    "g": "kVK_ANSI_G", "h": "kVK_ANSI_H", "i": "kVK_ANSI_I", "j": "kVK_ANSI_J", "k": "kVK_ANSI_K", "l": "kVK_ANSI_L",
    "m": "kVK_ANSI_M", "n": "kVK_ANSI_N", "o": "kVK_ANSI_O", "p": "kVK_ANSI_P", "q": "kVK_ANSI_Q", "r": "kVK_ANSI_R",
    "s": "kVK_ANSI_S", "t": "kVK_ANSI_T", "u": "kVK_ANSI_U", "v": "kVK_ANSI_V", "w": "kVK_ANSI_W", "x": "kVK_ANSI_X",
    "y": "kVK_ANSI_Y", "z": "kVK_ANSI_Z",
    "0": "kVK_ANSI_0", "1": "kVK_ANSI_1", "2": "kVK_ANSI_2", "3": "kVK_ANSI_3", "4": "kVK_ANSI_4",
    "5": "kVK_ANSI_5", "6": "kVK_ANSI_6", "7": "kVK_ANSI_7", "8": "kVK_ANSI_8", "9": "kVK_ANSI_9",
}.items():
    _add(ch, cname)

aliases = {
    "space": "kVK_Space", "spacebar": "kVK_Space", "tab": "kVK_Tab", "return": "kVK_Return",
    "enter": "kVK_ANSI_KeypadEnter",
    "escape": "kVK_Escape", "esc": "kVK_Escape",
    "left": "kVK_LeftArrow", "right": "kVK_RightArrow", "up": "kVK_UpArrow", "down": "kVK_DownArrow",
    "f1": "kVK_F1", "f2": "kVK_F2", "f3": "kVK_F3", "f4": "kVK_F4", "f5": "kVK_F5", "f6": "kVK_F6", "f7": "kVK_F7",
    "f8": "kVK_F8", "f9": "kVK_F9", "f10": "kVK_F10", "f11": "kVK_F11", "f12": "kVK_F12",
    "minus": "kVK_ANSI_Minus", "equal": "kVK_ANSI_Equal", "slash": "kVK_ANSI_Slash", "backslash": "kVK_ANSI_Backslash",
    "comma": "kVK_ANSI_Comma", "period": "kVK_ANSI_Period", "semicolon": "kVK_ANSI_Semicolon",
    "quote": "kVK_ANSI_Quote",
}
for k, c in aliases.items():
    _add(k, c)

VK.setdefault("space", 49); VK.setdefault("spacebar", 49)
VK.setdefault("tab", 48);   VK.setdefault("return", 36)
VK.setdefault("esc", 53);   VK.setdefault("escape", 53)
VK.setdefault("left", 123); VK.setdefault("right", 124)
VK.setdefault("down", 125); VK.setdefault("up", 126)

ansi_fallback = {
    "a": 0, "s": 1, "d": 2, "f": 3, "h": 4, "g": 5, "z": 6, "x": 7, "c": 8, "v": 9,
    "b": 11, "q": 12, "w": 13, "e": 14, "r": 15, "y": 16, "t": 17, "1": 18, "2": 19,
    "3": 20, "4": 21, "6": 22, "5": 23, "=": 24, "9": 25, "7": 26, "-": 27, "8": 28, "0": 29,
    "o": 31, "u": 32, "i": 34, "p": 35, "l": 37, "j": 38, "k": 40, "n": 45, "m": 46,
}
for k, v in ansi_fallback.items():
    VK.setdefault(k, v)

VK.update({
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97, "f7": 98, "f8": 100,
    "f9": 101, "f10": 109, "f11": 103, "f12": 111, "f13": 105, "f14": 107, "f15": 113, "f16": 106,
    "f17": 64, "f18": 79, "f19": 80, "f20": 90,
})

# ---------- флаги ----------
INTERESTING_MASK = (kCGEventFlagMaskShift
                    | kCGEventFlagMaskControl
                    | kCGEventFlagMaskAlternate
                    | kCGEventFlagMaskCommand)

MOD_MASKS = {
    "shift": kCGEventFlagMaskShift,
    "ctrl":  kCGEventFlagMaskControl,
    "alt":   kCGEventFlagMaskAlternate,
    "cmd":   kCGEventFlagMaskCommand,
}

def mods_from_flags(flags: int) -> tuple[str, ...]:
    flags &= INTERESTING_MASK
    out = []
    for name, mask in MOD_MASKS.items():
        if flags & mask:
            out.append(name)
    return tuple(sorted(out))

# ---------- конфиг ----------
def parse_hotkey(hs: str) -> Tuple[Tuple[str, ...], int]:
    parts = [p.strip().lower() for p in hs.split("+") if p.strip()]
    mods, key = [], None
    for p in parts:
        if p in ("cmd", "command"): mods.append("cmd")
        elif p in ("alt", "option"): mods.append("alt")
        elif p in ("ctrl", "control"): mods.append("ctrl")
        elif p == "shift": mods.append("shift")
        else: key = p
    if not key: raise ValueError(f"Hotkey '{hs}': нет основной клавиши")
    if key not in VK: raise ValueError(f"Hotkey '{hs}': неизвестная клавиша '{key}'")
    return tuple(sorted(mods)), VK[key]

def load_config(path: str):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    rules = []
    for item in data.get("hotkeys", []):
        mods, vk = parse_hotkey(item["hotkey"])
        rules.append({
            "mods": mods,
            "vk": vk,
            "action": item.get("action", "shell"),
            "cmd": item.get("cmd", ""),
            "swallow": bool(item.get("swallow", False))
        })
    return rules

# ---------- действия ----------
def run_action(rule: dict):
    if rule["action"] == "shell":
        cmd = rule["cmd"]
        if cmd:
            try:
                subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                )
            except subprocess.CalledProcessError as e:
                log(f"Code: {e.returncode}\nSTDERR: {e.stderr}")

# ---------- демон ----------
class HotkeyDaemon:
    def __init__(self, config_path: str):
        # НАСТОЯЩИЙ мьютекс вместо Event
        self._busy = threading.Lock()
        # набор виртуальных кодов, для которых мы проглотили keydown и ждём соответствующий keyup
        self._swallowing: set[int] = set()

        self.config_path = config_path
        self.rules = load_config(config_path)
        self._cfg_mtime = Path(config_path).stat().st_mtime
        self._rulemap_exact: Dict[Tuple[Tuple[str, ...], int], dict] = {}
        self._rebuild_cache()

    def _run_rule_blocking(self, rule: dict):
        try:
            run_action(rule)
        finally:
            # гарантированно отпускаем мьютекс
            try:
                self._busy.release()
            except RuntimeError:
                pass  # на всякий случай если уже отпущен

    def _rebuild_cache(self):
        # строим новую мапу и атомарно подменяем ссылку
        new_map: Dict[Tuple[Tuple[str, ...], int], dict] = {}
        for r in self.rules:
            new_map[(r["mods"], r["vk"])] = r
        self._rulemap_exact = new_map

    def _maybe_reload(self):
        try:
            mtime = Path(self.config_path).stat().st_mtime
            if mtime != self._cfg_mtime:
                self._cfg_mtime = mtime
                self.rules = load_config(self.config_path)
                self._rebuild_cache()
                log("[hotkeyd] config reloaded")
        except Exception as e:
            log("[hotkeyd] reload error:", e)

    def _find_rule(self, mods: Tuple[str, ...], vk: int) -> Optional[dict]:
        return self._rulemap_exact.get((mods, vk))

    def _callback(self, proxy, etype, event, refcon):
        # авто-реинициализация тапа
        if etype in (kCGEventTapDisabledByTimeout, kCGEventTapDisabledByUserInput):
            log("[hotkeyd] tap disabled -> re-enable")
            CGEventTapEnable(self.tap, True)
            return event

        # получаем коды в любом случае (нужно для keyup/keydown)
        vk = int(CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))

        # если мы ранее проглотили keydown — проглатываем и соответствующий keyup
        if etype == kCGEventKeyUp:
            if vk in self._swallowing:
                self._swallowing.discard(vk)
                return None
            return event

        if etype != kCGEventKeyDown:
            return event

        # не реагируем на авто-повторы
        if CGEventGetIntegerValueField(event, kCGKeyboardEventAutorepeat):
            return event

        mods = mods_from_flags(int(CGEventGetFlags(event)))
        rule = self._find_rule(mods, vk)
        if not rule:
            return event

        # Пытаемся АТОМАРНО захватить "занятость".
        if not self._busy.acquire(blocking=False):
            # занят: не запускаем действие, события не глотаем
            return event

        # мьютекс захвачен здесь, освобождает его работник в finally
        try:
            t = threading.Thread(target=self._run_rule_blocking, args=(rule,), daemon=True)
            t.start()
        except Exception:
            # если поток не запустился — не оставляем лок захваченным
            try:
                self._busy.release()
            except RuntimeError:
                pass
            raise

        if rule.get("swallow"):
            # глотаем keydown СЕЙЧАС и помечаем, чтобы проглотить и keyup
            self._swallowing.add(vk)
            return None

        return event

    def run(self):
        def reloader():
            while True:
                time.sleep(1.0)
                self._maybe_reload()

        threading.Thread(target=reloader, daemon=True).start()

        self.cb = self._callback  # держим сильную ссылку
        self.tap = CGEventTapCreate(
            kCGSessionEventTap, kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp),
            self.cb, None
        )
        if not self.tap:
            log("[hotkeyd] cannot create event tap. Give permissions in Input Monitoring (and Accessibility for swallow).")
            sys.exit(1)

        src = CFMachPortCreateRunLoopSource(None, self.tap, 0)
        CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes)
        CGEventTapEnable(self.tap, True)
        log("[hotkeyd] started. config:", self.config_path)
        CFRunLoopRun()

if __name__ == "__main__":
    cfg = sys.argv[1] if len(sys.argv) > 1 else str(Path.home() / ".hotkeyd.json")
    HotkeyDaemon(cfg).run()
