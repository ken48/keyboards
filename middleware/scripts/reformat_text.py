#!/usr/bin/env python3
# normalize text from clipboard: headings (hash) → capitalized + blank lines; optional numbering via flag; lists → normalized (with blank lines around), spaces fixed, sentences capitalized
# -*- coding: utf-8 -*-
import subprocess
import re
import time
from keyboard import FastKeyboard

# -----------------------------
# 0) Регекспы (предкомпиляция)

# Капитализация предложений
_CAPITALIZE_SENT_RE = re.compile(
    r'((?:^\s*(?:[—–-]\s+)?)|(?:[.!?]\s+))([a-zа-яё])',
    flags=re.IGNORECASE | re.MULTILINE
)

# Заголовки '#'
_H_RE = re.compile(r'^\s{0,3}(#{1,6})\s*(.+?)\s*$', re.MULTILINE)
_H_SENTINEL = "\x00H "  # скрытая метка для нумерованных заголовков

# Списки
_BULLET_RE  = re.compile(r'^(\s*)([-+*])\s*(.+?)\s*$', re.MULTILINE)
# ВАЖНО: не считаем строкой списка то, где после "1." сразу идёт "число."
_ORDERED_RE = re.compile(
    r'^(\s*)(\d+)([.)])\s+(?!\d+\.)\s*(.+?)\s*$',
    re.MULTILINE
)
_LIST_LINE_START = re.compile(r'^\s*(?:[-+*]\s+|\d+[.)]\s+)')  # начало пункта списка

# Пробелы / пунктуация внутри строки
_NUM_COLON_RE = re.compile(r'(\d)[ \t]*:[ \t]*(\d)')          # 13 : 30 -> 13:30, 13: 30 -> 13:30
# Для точки между числами ничего спец. не делаем — пробелы там не трогаем
_BEFORE_PUNCT = re.compile(r'\s+([,;:!?])')                   # пробел перед ,;:!?
_BEFORE_DOT   = re.compile(r'(?<!\d)\s+(\.)')                 # пробел перед точкой, если слева не цифра
_AFTER_PUNCT  = re.compile(r'(?<!\d)([,;:!?]+)(?=[0-9A-Za-zА-Яа-яЁё])')        # пробел после ,;:!? (если слева не цифра)
_MULTI_SPACE  = re.compile(r'[ \t]{2,}')                      # 2+ пробелов/табов

# Многократные пустые строки
_MANY_EMPTY_LINES_RE = re.compile(r'\n{3,}')


# -----------------------------
# 0) Капитализация предложений
def capitalize_block(text: str) -> str:
    if not text.strip():
        return text

    return _CAPITALIZE_SENT_RE.sub(
        lambda m: m.group(1) + m.group(2).upper(),
        text
    )


def _cap_first(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


# -----------------------------
# 1) Заголовки: "#", "##", ... → "1.", "1.1.", ... (опционально)

def convert_md_headings_to_numbered(text: str) -> str:
    """Заменяет '# ...' на нумерованные заголовки со снятием решёток.
       Добавляет sentinel, чтобы потом корректно расставить пустые строки."""
    counters = [0] * 6  # уровни H1..H6

    def on_heading(m: re.Match) -> str:
        hashes, title = m.group(1), _cap_first(m.group(2))
        level = len(hashes)
        counters[level - 1] += 1
        for i in range(level, 6):
            counters[i] = 0
        numbering = '.'.join(str(counters[i]) for i in range(level) if counters[i] > 0)
        return f"{_H_SENTINEL}{numbering}. {title}"

    return _H_RE.sub(on_heading, text)


def normalize_md_hash_headings(text: str) -> str:
    """Оставляет '# ...' как есть, но:
       — капитализирует первую букву после решёток,
       — добавляет пустые строки до/после (если не начало/конец и соседние строки не пустые)."""
    lines = text.split('\n')
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = _H_RE.match(line)
        if m:
            hashes, title = m.group(1), _cap_first(m.group(2))
            # пустая строка сверху (если не самая первая строка и сверху не пусто)
            if out and out[-1].strip() != "":
                out.append("")
            out.append(f"{hashes} {title}".rstrip())
            # пустая строка снизу (если дальше есть непустая строка)
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                out.append("")
            i += 1
            continue
        else:
            out.append(line.rstrip())
            i += 1

    text = '\n'.join(out)
    # 3+ пустых -> 2
    return _MANY_EMPTY_LINES_RE.sub('\n\n', text)


# -----------------------------
# 2) Списки: нормализация отступов (построчно, сохраняем пустые строки)

def normalize_list_indents(text: str, indent_size: int = 2) -> str:
    out_lines = []
    for line in text.split('\n'):
        m_b = _BULLET_RE.match(line)
        m_o = _ORDERED_RE.match(line)

        if m_b:
            _, marker, body = m_b.groups()
            out_lines.append(f"- {body.strip()}")  # ровно уровень 0
        elif m_o:
            _, num, closer, body = m_o.groups()
            out_lines.append(f"{num}{closer} {body.strip()}")  # тоже уровень 0
        else:
            out_lines.append(line.rstrip())

    return '\n'.join(out_lines)



# -----------------------------
# 3) Пробелы (построчно, без трогания '\n')

def normalize_spaces(text: str) -> str:
    lines = text.split('\n')
    new_lines = []

    for line in lines:
        # 1) Числовые конструкции с двоеточием: 13 : 30 → 13:30, 13: 30 → 13:30
        line = _NUM_COLON_RE.sub(r'\1:\2', line)

        # 2) убрать лишние пробелы перед пунктуацией
        line = _BEFORE_PUNCT.sub(r'\1', line)
        # перед точкой — только если слева НЕ цифра (чтобы не трогать 1.1, 3.14 и т.п.)
        line = _BEFORE_DOT.sub(r'\1', line)

        # 3) добавить пробел после пунктуации (, ; : ! ?), если дальше не пробел
        # и слева не цифра → не трогаем "13:30"
        line = _AFTER_PUNCT.sub(r'\1 ', line)

        # 4) схлопнуть множественные пробелы/табы
        line = _MULTI_SPACE.sub(' ', line)

        # 5) убрать хвостовые пробелы
        new_lines.append(line.rstrip())

    text = '\n'.join(new_lines)

    # 6) 3+ пустых строк -> 2
    return _MANY_EMPTY_LINES_RE.sub('\n\n', text)


# -----------------------------
# 3.1) Пустые строки вокруг списков и нумерованных заголовков

def ensure_blanklines_around_blocks(text: str) -> str:
    """Работает только с НУМЕРОВАННЫМИ заголовками (через sentinel) и списками.
       Заголовки с '#' обрабатываются отдельной функцией normalize_md_hash_headings()."""
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
            if i + 1 < len(lines) and lines[i + 1].strip() != "":
                out.append("")
            i += 1
            continue

        # --- Список: пустая строка перед первым пунктом и после последнего ---
        if is_list:
            # если список начинается с первой строки файла — сверху не добавляем пустую строку
            if not in_list and not prev_is_blank() and out:
                out.append("")       # начало списка (не в самом начале файла)
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
    text = _MANY_EMPTY_LINES_RE.sub('\n\n', text)
    return text


# -----------------------------
# 4) Порядок трансформаций

def transform_text(md_text: str, numbered_headings: bool = False) -> str:
    if numbered_headings:
        # Нумерация заголовков (решётки удаляются), потом расставим отступы через sentinel
        md_text = convert_md_headings_to_numbered(md_text)
    else:
        # Без нумерации: привести '#'-заголовки (капитализация + пустые строки)
        md_text = normalize_md_hash_headings(md_text)

    # Общее для обоих режимов
    md_text = normalize_list_indents(md_text, indent_size=2)
    md_text = normalize_spaces(md_text)
    # ВАЖНО: всегда расставляем пустые строки вокруг списков (и нумерованных заголовков, если они есть)
    md_text = ensure_blanklines_around_blocks(md_text)
    md_text = capitalize_block(md_text)
    return md_text


# -----------------------------
# 5) Основная функция

def normalize(select_all: bool = False, numbered_headings: bool = False):
    start_ts = time.perf_counter()
    keyboard = FastKeyboard()
    original = subprocess.run(['pbpaste'], capture_output=True, text=True, encoding="utf-8").stdout
    had_original = bool(original)
    try:
        if select_all:
            keyboard.send_select_all()
            time.sleep(0.07)

        keyboard.send_copy()
        time.sleep(0.17)

        text = subprocess.run(['pbpaste'], capture_output=True, text=True, encoding="utf-8").stdout
        if not text.strip():
            return

        transformed = transform_text(text, numbered_headings=numbered_headings)
        subprocess.run(['pbcopy'], input=transformed, text=True, encoding="utf-8")
        keyboard.send_paste()
        time.sleep(0.07)

    finally:
        subprocess.run(['pbcopy'], input=original if had_original else '', text=True, encoding="utf-8")
        duration = time.perf_counter() - start_ts
        print(f'duration: {duration:.3f} sec.', flush=True)


# -----------------------------
if __name__ == "__main__":
    from sys import argv
    select_all = ('--select-all' in argv)
    # по умолчанию без нумерации; '--numbered-headings' включает нумерацию
    numbered_headings = ('--numbered-headings' in argv)
    normalize(select_all=select_all, numbered_headings=numbered_headings)
