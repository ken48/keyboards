#!/usr/bin/env python3
import subprocess
import time

from input_source import MacInputSourceManager
from keyboard import FastKeyboard

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
        return ''.join(en_to_ru.get(char, char) for char in text), 'ru'
    else:
        return ''.join(ru_to_en.get(char, char) for char in text), 'en'


def find_and_replace_last_sequence(text):
    if not text or text.isspace():
        return text

    max_chars = 10
    last_part = text[-max_chars:]
    converted_last_part, lang = fix_keyboard_layout(last_part)
    return text[:-max_chars] + converted_last_part, lang

def main():
    keyboard = FastKeyboard()
    input_manager = MacInputSourceManager()

    original = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

    try:
        keyboard.send_select_last_line()
        time.sleep(0.07)

        keyboard.send_copy()
        time.sleep(0.17)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout

        if not text.strip():
            return

        transformed, lang = find_and_replace_last_sequence(text)

        subprocess.run(['pbcopy'], input=transformed, text=True)
        keyboard.send_paste()

        if lang == 'en':
            input_manager.switch_by_id('org.sil.ukelele.keyboardlayout.en-sym.en-sym')
        elif lang == 'ru':
            input_manager.switch_by_id('org.sil.ukelele.keyboardlayout.ru_sym.ru-sym')
        else:
            print(f'STDERR: unknown lang {lang}.', flush=True)

        time.sleep(0.05)

    finally:
        if original:
            subprocess.run(['pbcopy'], input=original, text=True)

if __name__ == "__main__":
    main()