#!/usr/bin/env python3
import subprocess
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

def _keyevent(vk: int, is_down: bool):
    e = CGEventCreateKeyboardEvent(None, vk, is_down)
    CGEventPost(kCGHIDEventTap, e)


class FastKeyboard:
    def __init__(self):
        self.key_codes = {
            'left': 123,
            'c': 8,
            'v': 9
        }

        self.modifiers = {
            'sft': 0x20000,
            'ctl': 0x40000,
            'opt': 0x80000,
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

    def send_select_last_word(self):
        self.send_key('left', self.modifiers['sft'] | self.modifiers['opt'])

def fix_keyboard_layout(text, direction=None):
    en_to_ru = {
        'q': 'й',
        'w': 'ц',
        'e': 'у',
        'r': 'к',
        't': 'е',
        'y': 'н',
        'u': 'г',
        'i': 'ш',
        'o': 'з',
        'p': 'э',
        ']': 'ъ',
        'a': 'ф',
        's': 'ы',
        'd': 'в',
        'f': 'а',
        'g': 'п',
        'h': 'р',
        'j': 'о',
        'k': 'л',
        'l': 'д',
        ';': 'ж',
        'z': 'я',
        'x': 'ч',
        'c': 'с',
        'v': 'м',
        'b': 'и',
        'n': 'т',
        'm': 'ь',
        ',': 'б',
        '.': 'ю',
        '/': 'х',
        'Q': 'Й',
        'W': 'Ц',
        'E': 'У',
        'R': 'К',
        'T': 'Е',
        'Y': 'Н',
        'U': 'Г',
        'I': 'Ш',
        'O': 'З',
        'P': 'Э',
        'A': 'Ф',
        'S': 'Ы',
        'D': 'В',
        'F': 'А',
        'G': 'П',
        'H': 'Р',
        'J': 'О',
        'K': 'Л',
        'L': 'Д',
        ':': 'Ж',
        'Z': 'Я',
        'X': 'Ч',
        'C': 'С',
        'V': 'М',
        'B': 'И',
        'N': 'Т',
        'M': 'Ь',
        '<': 'Б',
        '>': 'Ю',
        '?': 'Х',
    }

    ru_to_en = {v: k for k, v in en_to_ru.items()}

    en_chars = sum(1 for char in text if char in en_to_ru)
    ru_chars = sum(1 for char in text if char in ru_to_en)

    if en_chars > ru_chars:
        return ''.join(en_to_ru.get(char, char) for char in text)
    else:
        return ''.join(ru_to_en.get(char, char) for char in text)


def find_and_replace_last_sequence(text):
    if not text or text.isspace():
        return text

    return fix_keyboard_layout(text)

def main():
    keyboard = FastKeyboard()

    original = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

    try:
        keyboard.send_select_last_word()
        time.sleep(0.07)

        keyboard.send_copy()
        time.sleep(0.12)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

        if not text.strip():
            return

        transformed = find_and_replace_last_sequence(text)

        subprocess.run(['pbcopy'], input=transformed, text=True)
        keyboard.send_paste()

        time.sleep(0.05)

    finally:
        if original:
            subprocess.run(['pbcopy'], input=original, text=True)

if __name__ == "__main__":
    main()