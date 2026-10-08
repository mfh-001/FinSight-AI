"""Renders docs/media/demo.gif from real `finsight ask` output (a drawn terminal, not a screen capture).
Run from the repo root with FINSIGHT_HOME pointing at a folder where samples/ was ingested."""
import subprocess
import textwrap
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

QUESTIONS = [
    "What were Apple's total net sales in fiscal 2023?",
    "What was Apple's diluted earnings per share in fiscal 2023?",
    "How many bitcoin does Apple hold?",
]
W, H, PAD, SIZE = 1000, 520, 24, 17
font = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", SIZE)
LH = SIZE + 6
COLS = (W - 2 * PAD) // int(font.getlength("M"))


def run(q):
    out = subprocess.run(["finsight", "--backend", "none", "ask", q], capture_output=True, text=True).stdout
    lines = []
    for ln in out.splitlines():
        if ln.startswith("(no model") or not ln.strip():
            continue
        lines += textwrap.wrap(ln, COLS) or [""]
    return lines[:11]


def frame(lines, colors):
    im = Image.new("RGB", (W, H), (22, 24, 28))
    d = ImageDraw.Draw(im)
    for i, (ln, c) in enumerate(zip(lines, colors)):
        d.text((PAD, PAD + i * LH), ln, font=font, fill=c)
    return im


frames, durs = [], []
GREEN, WHITE, GREY, BLUE = (120, 220, 140), (230, 230, 230), (150, 150, 150), (120, 180, 255)
for q in QUESTIONS:
    cmd = f'$ finsight ask "{q}"'
    for n in range(0, len(cmd) + 1, 3):
        frames.append(frame([cmd[:n]], [GREEN]))
        durs.append(60)
    ans = run(q)
    shown, cols = [cmd], [GREEN]
    for ln in ans:
        shown.append(ln)
        cols.append(BLUE if ln.startswith("sources") or ln.startswith("[") else WHITE)
        frames.append(frame(shown, cols))
        durs.append(450)
    durs[-1] = 3500
out = Path(__file__).parent / "demo.gif"
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durs, loop=0, optimize=True)
print(out, len(frames), "frames")
