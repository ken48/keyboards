#!/usr/bin/env python3
import subprocess
import re
import time

from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    CGEventSetFlags,
    CGEventCreate,
    CGEventSetIntegerValueField,
    kCGKeyboardEventKeycode,
    kCGEventKeyDown,
    kCGEventKeyUp
)


class FastKeyboard:
    def __init__(self):
        self.key_codes = {
            'a': 0,
            'c': 8,
            'v': 9
        }

        self.modifiers = {
            'ctrl':0x40000,
            'shift': 0x20000,
            'alt': 0x80000,
            'cmd': 0x100000
        }

    def send_key(self, key_name, modifier_flags=0):
        if key_name in self.key_codes:
            key_code = self.key_codes[key_name]

            # Key down
            event_down = CGEventCreateKeyboardEvent(None, key_code, True)
            if modifier_flags:
                CGEventSetFlags(event_down, modifier_flags)
            CGEventPost(kCGHIDEventTap, event_down)

            # Key up
            event_up = CGEventCreateKeyboardEvent(None, key_code, False)
            if modifier_flags:
                CGEventSetFlags(event_up, modifier_flags)
            CGEventPost(kCGHIDEventTap, event_up)


    def send_copy(self):
        self.send_key('c', self.modifiers['cmd'])

    def send_paste(self):
        self.send_key('v', self.modifiers['cmd'])

    def send_select_all(self):
        self.send_key('a', self.modifiers['cmd'])


def capitalize_block(text: str) -> str:
    if not text.strip():
        return text

    pattern = r'((?:^\s*(?:[—–-]\s+)?)|(?:[.!?]\s+))([a-zа-яё])'

    return re.sub(
        pattern,
        lambda m: m.group(1) + m.group(2).upper(),
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )


def capitalize(select_block=False):
    keyboard = FastKeyboard()

    original = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

    try:
        if select_block:
            keyboard.send_select_all()
            time.sleep(0.07)

        keyboard.send_copy()
        time.sleep(0.17)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

        if not text.strip():
            return

        transformed = capitalize_block(text)

        subprocess.run(['pbcopy'], input=transformed, text=True)
        keyboard.send_paste()

        time.sleep(0.05)

    finally:
        if original:
            subprocess.run(['pbcopy'], input=original, text=True)


if __name__ == "__main__":
    import sys

    capitalize('--select-all' in sys.argv)