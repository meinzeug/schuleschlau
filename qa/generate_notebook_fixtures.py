#!/usr/bin/env python3
"""Create original, clearly synthetic notebook material for interface tests."""

import argparse
import json
import os
from hashlib import sha256
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, required=True, help="New empty output directory")
args = parser.parse_args()
OUT = args.out.resolve()
OUT.mkdir(mode=0o700, parents=True, exist_ok=False)
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SERIF = "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf"


def font(n, path=REG):
    return ImageFont.truetype(path, n)


def line(d, y, text, *, x=105, size=36, color="#273448", face=REG):
    d.text((x, y), text, fill=color, font=font(size, face))


def frac(d, x, y, n, den, color="#245985"):
    d.text((x + 18, y), str(n), fill=color, font=font(45, BOLD))
    d.line((x, y + 57, x + 70, y + 57), fill=color, width=4)
    d.text((x + 18, y + 62), str(den), fill=color, font=font(45, BOLD))


def bars(d, x, y, count, filled, *, width=500):
    w = width / count
    for i in range(count):
        d.rectangle(
            (x + i * w, y, x + (i + 1) * w, y + 70),
            fill="#73b5ed" if i < filled else "#f1f7fb",
            outline="#244d6a",
            width=3,
        )


def base():
    im = Image.new("RGB", (1400, 1850), "#fffef9")
    d = ImageDraw.Draw(im)
    d.rectangle((30, 30, 1370, 1820), outline="#d6dde2", width=3)
    line(d, 1750, "KÜNSTLICHE TESTSEITE – KEINE ECHTEN SCHÜLERDATEN", size=24, color="#6f7884")
    return im, d


pages = []
im, d = base()
d.rectangle((65, 75, 1335, 205), fill="#e9f3fb")
line(d, 95, "ARBEITSBLATT  ·  Mathematik", size=46, face=BOLD)
line(d, 250, "Thema: Brüche als Teile eines Ganzen", size=43, face=BOLD)
line(d, 340, "1. Färbe drei von vier gleich großen Teilen.", size=35)
bars(d, 130, 410, 4, 3)
frac(d, 720, 375, 3, 4)
line(d, 570, "2. Ergänze: Ein Ganzes besteht aus vier Vierteln.", size=35)
line(d, 660, "3. Zeichne einen Balken für zwei Sechstel.", size=35)
bars(d, 130, 740, 6, 0)
pages.append(("arbeitsblatt", im))

im, d = base()
for y in range(140, 1680, 68):
    d.line((65, y, 1335, y), fill="#b9d9ef", width=2)
d.line((190, 80, 190, 1690), fill="#e99b9b", width=3)
line(d, 90, "MATHEMATIK  ·  HEFTER", x=215, size=48, face=BOLD, color="#274c84")
line(d, 220, "Unechte Brüche und gemischte Zahlen", x=215, size=40, face=BOLD, color="#274c84")
line(d, 330, "Ein Ganzes hat vier Viertel.", x=215, size=37, color="#274c84")
frac(d, 230, 435, 5, 4, "#274c84")
line(d, 478, "=  1 Ganzes und 1 Viertel", x=330, size=42, color="#274c84")
bars(d, 230, 615, 4, 4, width=440)
bars(d, 230, 720, 4, 1, width=440)
line(d, 860, "Merke: 5 : 4 = 1 Rest 1.", x=215, size=37, color="#274c84")
pages.append(("hefter", im))

im, d = base()
d.rectangle((60, 75, 1340, 180), fill="#fff0c2")
line(d, 95, "ARBEITSHEFT  ·  Brüche üben", size=44, face=BOLD)
line(d, 250, "Seite 14     Aufgabe A", size=39, face=BOLD)
line(d, 345, "Wie viele Viertel sind in zwei Ganzen?", size=36)
bars(d, 130, 430, 4, 4)
bars(d, 130, 530, 4, 4)
line(d, 675, "Antwort: 2 Ganze = ______ Viertel", size=40)
line(d, 830, "Aufgabe B: Setze das passende Zeichen ein.", size=37, face=BOLD)
line(d, 920, "3/4     ____     1/4", size=44)
pages.append(("arbeitsheft", im))

im, d = base()
d.rectangle((75, 80, 150, 150), fill="#456fa1")
line(d, 90, "BUCHSEITE", x=180, size=45, face=BOLD)
line(d, 235, "Brüche vergleichen", size=54, face=SERIF)
line(d, 335, "Gleichnamige Brüche haben denselben Nenner.", size=34, face=SERIF)
line(d, 400, "Dann vergleichst du die Zahl der gefärbten Teile.", size=34, face=SERIF)
frac(d, 150, 520, 1, 4)
bars(d, 270, 550, 4, 1, width=500)
frac(d, 150, 700, 3, 4)
bars(d, 270, 730, 4, 3, width=500)
line(d, 900, "Drei Viertel sind größer als ein Viertel.", size=37, face=SERIF)
pages.append(("buchseite", im))

im, d = base()
d.rectangle((70, 75, 1330, 185), outline="#333333", width=3)
line(d, 96, "KLASSENARBEIT  ·  Mathematik", size=43, face=BOLD)
line(d, 250, "Übungstest: Brüche", size=43, face=BOLD)
line(d, 340, "1. Ergänze:  1 Ganzes = ____ Viertel.", size=36)
line(d, 440, "2. Vergleiche:  3/4  ____  1/4", size=36)
line(d, 540, "3. Wandle um:  5/4 = ____ Ganze und ____ Viertel.", size=36)
line(d, 720, "Beispielantwort: 1 Ganzes und 1 Viertel", size=35, color="#28599a")
line(d, 810, "Kontrollnotiz: richtig", size=34, color="#bf334a")
pages.append(("klassenarbeit", im))

manifest = []
for name, im in pages:
    target = OUT / f"{name}.jpg"
    im.save(target, "JPEG", quality=91, optimize=True)
    os.chmod(target, 0o600)
    manifest.append(
        {
            "name": name,
            "file": target.name,
            "sha256": sha256(target.read_bytes()).hexdigest(),
            "size": target.stat().st_size,
        }
    )
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
os.chmod(OUT / "manifest.json", 0o600)
print(json.dumps(manifest, ensure_ascii=False))
