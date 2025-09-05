#!/usr/bin/env python3
import subprocess
import re
import time
from keyboard import FastKeyboard


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
    start_ts = time.perf_counter()

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

        time.sleep(0.07)

    finally:
        if original:
            subprocess.run(['pbcopy'], input=original, text=True)

        duration = time.perf_counter() - start_ts
        print(f'duration: {duration:.3f} sec.', flush=True)


if __name__ == "__main__":
    import sys

    capitalize('--select-all' in sys.argv)