#!/usr/bin/env python3
import subprocess
import time
import re

KEYSTROKE_SELECT_LAST_WORD = "key code 123 using {shift down, option down}"
KEYSTROKE_TOGGLE_LAYOUT = "key code 49 using {control down}"
KEYSTROKE_COPY = "key code 8 using command down"
KEYSTROKE_PASTE = "key code 9 using command down"

def run_applescript(script):
    process = subprocess.run(['osascript', '-e', script], 
                          capture_output=True, text=True)
    if process.returncode != 0:
        print(f"Error: {process.stderr}")
    return process.stdout

def run_keystroke(keystroke, need_wait=True):
    retstdout = run_applescript(f'tell application "System Events" to {keystroke}')

    if need_wait:
        time.sleep(0.15)

    return retstdout

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

    try:
        original_clipboard = subprocess.run(['pbpaste'], capture_output=True, text=True)
        original_content = original_clipboard.stdout if original_clipboard.returncode == 0 else ""
    except:
        original_content = ""

    run_keystroke(KEYSTROKE_SELECT_LAST_WORD)

    try:
        run_keystroke(KEYSTROKE_COPY)

        result = subprocess.run(['pbpaste'], capture_output=True, text=True)
        if result.returncode == 0:
            full_text = result.stdout
            final_text = find_and_replace_last_sequence(full_text)

            process = subprocess.run(['pbcopy'], input=final_text, text=True)
            if process.returncode == 0:
                run_keystroke(KEYSTROKE_PASTE, need_wait=False)
                run_keystroke(KEYSTROKE_TOGGLE_LAYOUT)
            else:
                print("Failed to copy to clipboard")
        else:
            print("No text available")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if original_content:
            subprocess.run(['pbcopy'], input=original_content, text=True)

if __name__ == "__main__":
    main()