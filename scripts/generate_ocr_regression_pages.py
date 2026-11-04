"""Generate synthetic OCR challenge pages; no accounts, network or real school data.

The checked-in manifest is the reference. Re-generation is not a human review
and pixel output may differ with font or Pillow versions.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1] / 'testdata' / 'ocr_synthetic'
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
HAND = '/usr/share/fonts/opentype/urw-base35/Z003-MediumItalic.otf'


def setup():
    image = Image.new('RGB', (1000, 1400), 'white')
    draw = ImageDraw.Draw(image)
    return image, draw


def text(draw, xy, value, size=30, font=FONT, fill=(15, 20, 30)):
    draw.text(xy, value, font=ImageFont.truetype(font, size), fill=fill)


def run():
    ROOT.mkdir(parents=True, exist_ok=True)
    image, draw = setup()
    text(draw, (70, 55), 'Brüche und Einheiten', 42)
    text(draw, (70, 140), 'Ein Bruch beschreibt Teile eines Ganzen.')
    text(draw, (70, 190), 'Der Nenner nennt die Anzahl der Teile.')
    text(draw, (70, 270), 'Beispiel:')
    # Two vertically stacked operands deliberately test spatial reading.
    text(draw, (255, 252), '2', 30)
    draw.line((248, 294, 283, 294), fill='black', width=3)
    text(draw, (255, 300), '3', 30)
    text(draw, (310, 275), 'Minute = 40 Sekunden')
    text(draw, (70, 400), 'Wert', 29)
    text(draw, (370, 400), 'Einheit', 29)
    draw.rectangle((60, 395, 760, 570), outline='black', width=2)
    draw.line((60, 447, 760, 447), fill='black', width=2)
    draw.line((330, 395, 330, 570), fill='black', width=2)
    text(draw, (70, 470), '1 km')
    text(draw, (370, 470), '1000 m')
    text(draw, (70, 640), 'Merke: erst die Einheit prüfen!', 34, HAND, (110, 20, 20))
    # Three equal segments, two shaded; visually represents the same fraction.
    draw.rectangle((70, 750, 730, 850), outline='black', width=3)
    draw.rectangle((72, 752, 508, 848), fill=(75, 165, 220))
    for x in (290, 510):
        draw.line((x, 750, x, 850), fill='black', width=3)
    image.save(ROOT / '01_bruch_tabelle.png', optimize=True)

    image, draw = setup()
    text(draw, (70, 55), 'Satzglieder erkennen', 42)
    text(draw, (70, 150), 'Heute entdeckt Lina einen alten Brief.')
    text(draw, (70, 210), 'Lina liest den Brief zu Hause.')
    text(draw, (70, 320), 'Hinweis am Rand:', 30)
    text(draw, (70, 380), 'Wer oder was?', 42, HAND, (70, 25, 120))
    text(draw, (70, 550), 'Kurze Notiz: Subjekt erfragen.')
    # Last phrase is intentionally wholly obscured; ground truth never asks the
    # recognizer to infer the known but now invisible characters.
    text(draw, (70, 720), 'Unklar: verborgenes Wort')
    draw.rectangle((190, 710, 620, 765), fill=(70, 70, 70))
    image.save(ROOT / '02_deutsch_verdeckt.png', optimize=True)

    image, draw = setup()
    text(draw, (70, 55), 'Wasserkreislauf', 42)
    text(draw, (70, 150), 'Wasser verdunstet durch Wärme.')
    text(draw, (70, 205), 'Wasserdampf kühlt ab und bildet Wolken.')
    text(draw, (70, 260), 'Aus Wolken fällt Niederschlag.')
    draw.ellipse((120, 480, 260, 620), fill=(250, 196, 45), outline='black', width=3)
    draw.ellipse((550, 440, 830, 560), fill=(185, 195, 210), outline='black', width=3)
    draw.line((270, 550, 520, 500), fill=(30, 80, 170), width=5)
    draw.polygon(((520, 500), (494, 493), (502, 517)), fill=(30, 80, 170))
    text(draw, (155, 640), 'Sonne')
    text(draw, (630, 600), 'Wolke')
    # Deliberate crop, mild downsampling and rotation, all reproducible.
    image = image.crop((25, 10, 970, 1120)).resize((756, 888), Image.Resampling.LANCZOS)
    image = image.rotate(2, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(210, 210, 210))
    image.save(ROOT / '03_wasser_schief.jpg', quality=62, optimize=True)


if __name__ == '__main__':
    run()
