#lsof | grep tty.usbserial-AB9NYYK4
#kill -9 (the first number as a result of the command)
#for example
#kill -9 68034

import serial
import textwrap
from tkinter import Tk, filedialog
import unicodedata
import os
from PIL import Image
import time

# ---Printer Config---

#this is the path on sonyas mac
#printer_path = '/dev/tty.usbserial-AB9NYYK4'
# For windows computers go to Device Manager, click on Ports (COM & LPT) and find which COM yours is on
printer_path = 'COM4'
printer = serial.Serial(printer_path, 9600)

# ---helper to send ESC-prefixed codes-------------------
def esc(seq):
    printer.write(b'\x1B' + seq)

def reset_printer():
    # software reset → back to factory defaults
    esc(b'c')              # ESC c  (ImageWriter "reset defaults")
# -------------------------------------------------------

# ---.txt functions---
# this printer existed before unicode
char_replacements = {
    '“': '"', '”': '"',
    '‘': "'", '’': "'",
    '–': '-', '—': '-', '―': '-',
    '…': '...', '•': '*', '·': '.', '‐': '-', '‑': '-',
    ' ': ' ', ' ': ' ',
    '°': ' deg', '×': 'x', '÷': '/',
    '™': '(TM)', '®': '(R)', '©': '(C)',
    '¼': '1/4', '½': '1/2', '¾': '3/4',
    '†': '+', '‡': '++'
}
def clean_text(text):
    for orig, repl in char_replacements.items():
        text = text.replace(orig, repl)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', errors='ignore').decode('ascii')
    return text
def process_text_file(file_path):
    reset_printer()                       # restore 10 cpi, 6 lpi, etc. (so the text looks normal)
    file = open(file_path, 'r', encoding='utf-8')
    raw_text = file.read()
    file.close()

    # Wrap each paragraph manually - printer doesn't know to do that
    wrapped_lines = []
    chars_per_line = 80 # width of imagewriter II
    for paragraph in clean_text(raw_text).split('\n'):
        wrapped = textwrap.wrap(paragraph, width=chars_per_line)
        if not wrapped:
            wrapped_lines.append('')  # Preserve blank lines
        else:
            wrapped_lines.extend(wrapped)

    for line in wrapped_lines:
        printer.write((line + '\r\n').encode('ascii', errors='ignore'))

# ---image functions---
MAX_COLS = 576               # 8″ @ 72 dpi  (fits ImageWriter’s line)

def graphics_preamble():
    # 72 × 72 dpi grid & zero‑gap line spacing
    esc(b'n')     # 9 cpi  (72 dpi horiz)
    esc(b'T16')   # LF = 16/144 in (8 dots) → no vertical gap
    
def process_image_file(file_path):
    img = Image.open(file_path).convert('1')             # dither to 1‑bit
    w, h = img.size
    if w > MAX_COLS:                                # scale to 8 in wide
        h = h * MAX_COLS // w
        w = MAX_COLS
        img = img.resize((w, h), Image.LANCZOS)

    graphics_preamble()

    bands = (h + 7) // 8                            # rows of 8 pixels
    for band in range(bands):
        top = band * 8
        row = bytearray()
        for x in range(w):
            b = 0
            for bit in range(8):                    # LSB = row 0
                y = top + bit
                if y < h and img.getpixel((x, y)) == 0:
                    b |= 1 << bit
            row.append(b)

        # send slice
        esc(b'G' + f"{w:04d}".encode())             # ESC G nnnn
        printer.write(row)
        printer.write(b'\r\n')                      # print + 8‑dot LF
    printer.write(b'\r\n')                          # blank line after image
    reset_printer()                                 # leave printer sane

# ---CHOOSE YOUR FILE---
root = Tk()
root.withdraw()
file_path = filedialog.askopenfilename(
    filetypes=[("Supported Files", "*.txt *.png *.jpg *.jpeg *.webp")]
)

if not file_path:
    print("No file selected.")
    printer.close()
    exit()

ext = os.path.splitext(file_path)[1].lower()

if ext == '.txt':
    print("Printing text...")
    process_text_file(file_path)
elif ext in ['.png', '.jpg', '.jpeg','.webp']:
    print("Printing image...")
    process_image_file(file_path)
else:
    print(f"Unsupported file type: {ext}")

printer.write(b'\n' * 6)  # Eject the page
printer.close()

print('yippee')
