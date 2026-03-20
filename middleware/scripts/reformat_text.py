#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import subprocess
import time
from sys import argv

from keyboard import FastKeyboard

H_RE = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$')
BULLET_RE = re.compile(r'^(\s*)[-+*]\s*(.+?)\s*$')
ORDERED_RE = re.compile(r'^(\s*)(\d+)([.)])\s+(?!\d+\.)\s*(.+?)\s*$')
LIST_RE = re.compile(r'^\s*(?:[-+*]\s+|\d+[.)]\s+)')
CAP_RE = re.compile(r'((?:^\s*(?:[—–-]\s+)?)|(?:[.!?]\s+))([a-zа-яё])', re.IGNORECASE)

# текст - текст / текст, - текст / текст -, текст
TEXT_DASH_TEXT_RE = re.compile(r'(?<=\S)(?:,?\s)-(?=\s,?\S)')
NUM_COLON_RE = re.compile(r'(\d)[ \t]*:[ \t]*(\d)')
BEFORE_PUNCT_RE = re.compile(r'\s+([,;:!?])')
BEFORE_DOT_RE = re.compile(r'(?<!\d)\s+(\.)')
AFTER_PUNCT_RE = re.compile(r'(?<!\d)([,;:!?]+)(?=[0-9A-Za-zА-Яа-яЁё])')
MULTI_SPACE_RE = re.compile(r'[ \t]{2,}')
MANY_EMPTY_LINES_RE = re.compile(r'\n{3,}')
QUOTE_TRANS = str.maketrans({'«': '"', '»': '"', '„': '"', '“': '"', '‟': '"'})


def cap_first(text: str) -> str:
    return text[:1].upper() + text[1:] if text else text


def is_list_line(line: str) -> bool:
    return bool(LIST_RE.match(line))


def normalize_inline(line: str) -> str:
    line = line.translate(QUOTE_TRANS)
    line = TEXT_DASH_TEXT_RE.sub(' —', line)
    line = NUM_COLON_RE.sub(r'\1:\2', line)
    line = BEFORE_PUNCT_RE.sub(r'\1', line)
    line = BEFORE_DOT_RE.sub(r'\1', line)
    line = AFTER_PUNCT_RE.sub(r'\1 ', line)
    line = MULTI_SPACE_RE.sub(' ', line)
    return line.rstrip()


def capitalize_sentences(line: str) -> str:
    return CAP_RE.sub(lambda m: m.group(1) + m.group(2).upper(), line)


def normalize_lines(text: str, numbered_headings: bool = False) -> list[str]:
    out: list[str] = []
    counters = [0] * 6

    for raw in text.splitlines():
        line = raw.rstrip()

        m = H_RE.match(line)
        if m:
            hashes, title = m.groups()
            title = cap_first(normalize_inline(title.strip()))
            if numbered_headings:
                level = len(hashes)
                counters[level - 1] += 1
                for i in range(level, 6):
                    counters[i] = 0
                prefix = '.'.join(str(counters[i]) for i in range(level) if counters[i])
                line = f'{prefix}. {title}'
            else:
                line = f'{hashes} {title}'
        else:
            m = BULLET_RE.match(line)
            if m:
                line = f'- {normalize_inline(m.group(2).strip())}'
            else:
                m = ORDERED_RE.match(line)
                if m:
                    line = f'{m.group(2)}{m.group(3)} {normalize_inline(m.group(4).strip())}'
                else:
                    line = normalize_inline(line)

            if not is_list_line(line):
                line = capitalize_sentences(line)

        out.append(line)

    return out


def add_structural_spacing(lines: list[str]) -> str:
    out: list[str] = []
    n = len(lines)

    for i, line in enumerate(lines):
        current_is_list = is_list_line(line)
        prev_is_list = i > 0 and is_list_line(lines[i - 1])
        next_is_list = i + 1 < n and is_list_line(lines[i + 1])

        if current_is_list and out and out[-1].strip() and not prev_is_list:
            out.append('')

        if H_RE.match(line):
            if out and out[-1].strip():
                out.append('')
            out.append(line)
            if i + 1 < n and lines[i + 1].strip():
                out.append('')
            continue

        out.append(line)

        if current_is_list and not next_is_list and i + 1 < n and lines[i + 1].strip():
            out.append('')

    return MANY_EMPTY_LINES_RE.sub('\n\n', '\n'.join(out))


def transform_text(text: str, numbered_headings: bool = False) -> str:
    lines = normalize_lines(text, numbered_headings=numbered_headings)
    return add_structural_spacing(lines)


def normalize(select_all: bool = False, numbered_headings: bool = False) -> None:
    start_ts = time.perf_counter()
    keyboard = FastKeyboard()
    original = subprocess.run(['pbpaste'], capture_output=True, text=True, encoding='utf-8').stdout
    had_original = bool(original)

    try:
        if select_all:
            keyboard.send_select_all()
            time.sleep(0.05)

        keyboard.send_copy()
        time.sleep(0.15)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True, encoding='utf-8').stdout
        if not text.strip():
            return

        transformed = transform_text(text, numbered_headings=numbered_headings)
        subprocess.run(['pbcopy'], input=transformed, text=True, encoding='utf-8')
        keyboard.send_paste()
        time.sleep(0.05)
    finally:
        subprocess.run(['pbcopy'], input=original if had_original else '', text=True, encoding='utf-8')
        print(f'duration: {time.perf_counter() - start_ts:.3f} sec.', flush=True)


if __name__ == '__main__':
    normalize(
        select_all='--select-all' in argv,
        numbered_headings='--numbered-headings' in argv,
    )
