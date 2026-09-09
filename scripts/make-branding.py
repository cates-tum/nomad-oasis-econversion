#!/usr/bin/env python3
"""Generate placeholder "eConversion Nexus" branding images for the NOMAD GUI.

These overwrite the stock NOMAD logo files via bind mounts declared on the
`app` service in docker-compose.yaml. They are deliberately plain text marks,
meant to be replaced with a real logo later.

Output: configs/branding/
  nomad-text.png     621x111  dark wordmark, loading screen
  nomad-oasis.png    512x512  dark stacked mark, About page
  nomad.png          512x512  white stacked mark, dark nav bar
  favicon.png        128x126  dark "eN" monogram
  favicon-hres.png   512x512  dark "eN" monogram
  favicon.ico        multi-size, from the monogram

Run: python3 scripts/make-branding.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent.parent / "configs" / "branding"
DARK = (42, 42, 46, 255)
WHITE = (255, 255, 255, 255)

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _fit(draw, text, box_w, start):
    """Largest font size at which text fits box_w."""
    size = start
    while size > 8:
        f = font(size)
        if draw.textlength(text, font=f) <= box_w:
            return f
        size -= 2
    return font(8)


def wordmark(path, w, h, color):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _fit(d, "eConversion Nexus", w * 0.92, h)
    bbox = d.textbbox((0, 0), "eConversion Nexus", font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]),
           "eConversion Nexus", font=f, fill=color)
    im.save(path)


def stacked(path, size, color):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f_top = _fit(d, "eConversion", size * 0.86, int(size * 0.20))
    f_bot = _fit(d, "NEXUS", size * 0.86, int(size * 0.30))
    top_w = d.textlength("eConversion", font=f_top)
    bot_w = d.textlength("NEXUS", font=f_bot)
    d.text(((size - top_w) / 2, size * 0.34), "eConversion", font=f_top, fill=color)
    d.text(((size - bot_w) / 2, size * 0.52), "NEXUS", font=f_bot, fill=color)
    im.save(path)


def monogram(path, w, h, color):
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = _fit(d, "eN", w * 0.8, h)
    bbox = d.textbbox((0, 0), "eN", font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((w - tw) / 2 - bbox[0], (h - th) / 2 - bbox[1]), "eN", font=f, fill=color)
    im.save(path)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wordmark(OUT / "nomad-text.png", 621, 111, DARK)
    stacked(OUT / "nomad-oasis.png", 512, DARK)
    stacked(OUT / "nomad.png", 512, WHITE)
    monogram(OUT / "favicon.png", 128, 126, DARK)
    monogram(OUT / "favicon-hres.png", 512, 512, DARK)
    ico = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    dd = ImageDraw.Draw(ico)
    ff = _fit(dd, "eN", 256 * 0.8, 256)
    b = dd.textbbox((0, 0), "eN", font=ff)
    dd.text(((256 - (b[2] - b[0])) / 2 - b[0], (256 - (b[3] - b[1])) / 2 - b[1]),
            "eN", font=ff, fill=DARK)
    ico.save(OUT / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    for p in sorted(OUT.iterdir()):
        print(p.name, Image.open(p).size)


if __name__ == "__main__":
    main()
