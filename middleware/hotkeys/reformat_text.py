#!/usr/bin/env python3
# normalize text from clipboard: headings → numbered (with blank lines around), lists → normalized (with blank lines around), spaces fixed, sentences capitalized
# -*- coding: utf-8 -*-
import subprocess
import re
import time
from keyboard import FastKeyboard

# -----------------------------
# 0) Капитализация предложений
def capitalize_block(text: str) -> str:
    if not text.strip():
        return text
    # начало строки (с опциональным маркером списка-тире) ИЛИ .?! + пробельный разделитель
    pattern = r'((?:^\s*(?:[—–-]\s+)?)|(?:[.!?]\s+))([a-zа-яё])'
    return re.sub(
        pattern,
        lambda m: m.group(1) + m.group(2).upper(),
        text,
        flags=re.IGNORECASE | re.MULTILINE
    )

# -----------------------------
# 1) Заголовки: "#", "##", ... → "1.", "1.1.", ...
_H_RE = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.MULTILINE)
_H_SENTINEL = "\x00H "  # скрытая метка для нумерованных заголовков

def convert_md_headings_to_numbered(text: str) -> str:
    counters = [0] * 6  # уровни H1..H6
    def on_heading(m: re.Match) -> str:
        hashes, title = m.group(1), m.group(2).strip()
        level = len(hashes)
        counters[level - 1] += 1
        for i in range(level, 6):
            counters[i] = 0
        numbering = '.'.join(str(counters[i]) for i in range(level) if counters[i] > 0)
        # помечаем как заголовок (чтобы не спутать со списком)
        return f"{_H_SENTINEL}{numbering}. {title}"
    return _H_RE.sub(on_heading, text)

# -----------------------------
# 2) Списки: нормализация отступов (построчно, сохраняем пустые строки)
_BULLET_RE  = re.compile(r'^(\s*)([-+*])\s*(.+?)\s*$', re.MULTILINE)
_ORDERED_RE = re.compile(r'^(\s*)(\d+)([.)])\s*(.+?)\s*$', re.MULTILINE)

def normalize_list_indents(text: str, indent_size: int = 2) -> str:
    out_lines = []
    for line in text.split('\n'):
        m_b = _BULLET_RE.match(line)
        m_o = _ORDERED_RE.match(line)
        if m_b:
            leading, marker, body = m_b.groups()
            level = max(0, len(leading) // indent_size)
            out_lines.append(f"{' ' * (level * indent_size)}{marker} {body.strip()}")
        elif m_o:
            leading, num, closer, body = m_o.groups()
            level = max(0, len(leading) // indent_size)
            out_lines.append(f"{' ' * (level * indent_size)}{num}{closer} {body.strip()}")
        else:
            out_lines.append(line.rstrip())
    return '\n'.join(out_lines)

# -----------------------------
# 3) Пробелы
def normalize_spaces(text: str) -> str:
    # убрать лишние пробелы перед пунктуацией (кроме точки между цифрами)
    text = re.sub(r'\s+([,;:!?])', r'\1', text)
    text = re.sub(r'(?<!\d)\s+(\.)', r'\1', text)  # перед точкой, если слева не цифра

    # добавить пробел после пунктуации:
    # 1) для , ; : ! ? — всегда, если дальше не пробел
    text = re.sub(r'([,;:!?])(?=\S)', r'\1 ', text)
    # 2) для точки — только если слева НЕ цифра (не трогаем "1.1", "2.3.4")
    text = re.sub(r'(?<!\d)\.(?=\S)', '. ', text)

    # схлопнуть множественные пробелы/табы внутри строк
    text = re.sub(r'[ \t]{2,}', ' ', text)

    # убрать хвостовые пробелы
    text = '\n'.join(line.rstrip() for line in text.split('\n'))

    # 3+ пустых строк -> 2
    return re.sub(r'\n{3,}', '\n\n', text)

# -----------------------------
# 3.1) Пустые строки вокруг списков и нумерованных заголовков
_LIST_LINE_START = re.compile(r'^\s*(?:[-+*]\s+|\d+[.)]\s+)')  # начало пункта списка
def ensure_blanklines_around_blocks(text: str) -> str:
    lines = text.split('\n')
    out = []
    in_list = False

    def prev_is_blank() -> bool:
        return bool(out) and out[-1].strip() == ""

    i = 0
    while i < len(lines):
        line = lines[i]
        is_heading = line.startswith(_H_SENTINEL)
        is_list = (not is_heading) and bool(_LIST_LINE_START.match(line))

        # --- Нумерованный заголовок: пустая строка до и после ---
        if is_heading:
            if out and not prev_is_blank():
                out.append("")
            out.append(line)
            # пустая строка после, если следующая не пустая и не конец файла
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                out.append("")
            i += 1
            continue

        # --- Список: пустая строка перед первым пунктом и после последнего ---
        if is_list:
            if not in_list and not prev_is_blank():
                out.append("")       # начало списка
            in_list = True
            out.append(line)

            next_line = lines[i + 1] if i + 1 < len(lines) else ""
            next_is_heading = next_line.startswith(_H_SENTINEL)
            next_is_list = (not next_is_heading) and bool(_LIST_LINE_START.match(next_line))
            next_is_blank = next_line.strip() == ""

            # конец списка — если следующая строка не пункт списка
            if not next_is_list:
                if not next_is_blank:    # добавим пустую строку, если её нет
                    out.append("")
                in_list = False

            i += 1
            continue

        # обычная строка
        in_list = False
        out.append(line)
        i += 1

    # снять sentinel у заголовков и финально прибрать лишние пустые строки
    out = [l[len(_H_SENTINEL):] if l.startswith(_H_SENTINEL) else l for l in out]
    text = '\n'.join(out)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text

# -----------------------------
# 4) Порядок трансформаций
def transform_text(md_text: str) -> str:
    md_text = convert_md_headings_to_numbered(md_text)
    md_text = normalize_list_indents(md_text, indent_size=2)
    md_text = normalize_spaces(md_text)
    md_text = ensure_blanklines_around_blocks(md_text)
    md_text = capitalize_block(md_text)
    return md_text

# -----------------------------
# 5) Основная функция
def normalize(select_all: bool = False):
    start_ts = time.perf_counter()
    keyboard = FastKeyboard()
    original = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout
    had_original = bool(original)
    try:
        if select_all:
            keyboard.send_select_all()
            time.sleep(0.07)

        keyboard.send_copy()
        time.sleep(0.17)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True).stdout
        if not text.strip():
            return

        transformed = transform_text(text)
        subprocess.run(['pbcopy'], input=transformed, text=True)
        keyboard.send_paste()
        time.sleep(0.07)

    finally:
        subprocess.run(['pbcopy'], input=original if had_original else '', text=True)
        duration = time.perf_counter() - start_ts
        print(f'duration: {duration:.3f} sec.', flush=True)

# -----------------------------
if __name__ == "__main__":
    from sys import argv
    normalize('--select-all' in argv)
