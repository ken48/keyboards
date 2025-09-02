#!/usr/bin/env python3
import subprocess
import time
import re
import sys

KEYSTROKE_SELECT_BLOCK = "key code 126 using {shift down, option down}"
KEYSTROKE_COPY = "key code 8 using command down"
KEYSTROKE_PASTE = "key code 9 using command down"

def run_applescript(script):
    process = subprocess.run(['osascript', '-e', script], 
                          capture_output=True, text=True)
    if process.returncode != 0:
        print(f"Error: {process.stderr}")
    return process.stdout

def run_keystroke(keystroke):
    retstdout = run_applescript(f'tell application "System Events" to {keystroke}')
    time.sleep(0.15)
    return retstdout

def capitalize_sentences(text):
    if not text or text.isspace():
        return text
    
    lines = text.split('\n')
    processed_lines = []
    
    for line in lines:
        if line.strip():
            line = line[0].upper() + line[1:]

            processed_line = re.sub(
                r'([.!?])(\s*)([a-zа-яё])', 
                lambda m: m.group(1) + ' ' + m.group(3).upper(), 
                line
            )
            processed_lines.append(processed_line)
        else:
            processed_lines.append('')

    return '\n'.join(processed_lines)

def main():

    block_selection = len(sys.argv) > 1 and sys.argv[1] == "--select-block"

    try:
        original_clipboard = subprocess.run(['pbpaste'], capture_output=True, text=True)
        original_content = original_clipboard.stdout if original_clipboard.returncode == 0 else ""
    except:
        original_content = ""

    if block_selection:
        run_keystroke(KEYSTROKE_SELECT_BLOCK)
    
    try:
        run_keystroke(KEYSTROKE_COPY)
        
        result = subprocess.run(['pbpaste'], capture_output=True, text=True)
        if result.returncode == 0:
            original_text = result.stdout
            print(f"Original: {repr(original_text)}")
            
            transformed_text = capitalize_sentences(original_text)
            transformed_text = transformed_text.rstrip()
            print(f"Transformed: {repr(transformed_text)}")

            if len(transformed_text) > 0:
                process = subprocess.run(['pbcopy'], input=transformed_text, text=True)
                if process.returncode == 0:
                    run_keystroke(KEYSTROKE_PASTE)
                    print("Success! Text transformed and pasted.")
                else:
                    print("Failed to copy to clipboard")
        else:
            print("Failed to get text from clipboard")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if original_content:
            subprocess.run(['pbcopy'], input=original_content, text=True)

if __name__ == "__main__":
    main()