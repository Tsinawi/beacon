"""Local spotlight mockups for Glens of Bloomfield (1080x1350). Map-free designs: no street data needed."""
import math, sys, os
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps

D = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(D, "src")
OUT = os.path.join(D, "out"); os.makedirs(OUT, exist_ok=True)
W, H = 1080, 1350
NAVY, TEAL, CORAL, TAN, INK = (21, 58, 88), (85, 193, 199), (238, 143, 128), (246, 236, 214), (19, 42, 63)
GLENS = (47, 93, 70)
FD = "/usr/share/fonts/opentype/inter/"
def F(w, s): return ImageFont.truetype(FD + {"b": "InterDisplay-Bold.otf", "xb": "InterDisplay-ExtraBold.otf", "m": "InterDisplay-Medium.otf", "r": "Inter-Regular.otf", "sb": "Inter-SemiBold.otf"}[w], s)

logo = Image.open(os.path.join(SRC, "6b9a6fe3f8b55750b9468e9d1f47fe2d.png")).convert("RGBA")
def logo_tone(color, width):
    a = logo.split()[3]
    solid = Image.new("RGBA", logo.size, color + (255,)); solid.putalpha(a)
    return solid.resize((width, round(logo.height * width / logo.width)), Image.LANCZOS)

def eho(d, color, y=H - 46):
    t = "Equal Housing Opportunity"
    f = F("sb", 22); w = d.textlength(t, font=f)
    # small house mark
    x = (W - w - 40) / 2
    d.polygon([(x, y + 12), (x + 14, y), (x + 28, y + 12)], outline=color, width=3)
    d.rectangle([x + 5, y + 12, x + 23, y + 26], outline=color, width=3)
    d.text((x + 40, y + 1), t, font=f, fill=color)

def wrap(d, text, font, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=font) <= maxw: cur = t
        else: lines.append(cur); cur = w_
    lines.append(cur); return lines

def pin(d, x, y, r, fill, hole):
    cy = y - r * 2.1
    d.polygon([(x - r * .86, cy + r * .5), (x + r * .86, cy + r * .5), (x, y)], fill=fill)
    d.ellipse([x - r, cy - r, x + r, cy + r], fill=fill)
    d.ellipse([x - r * .4, cy - r * .4, x + r * .4, cy + r * .4], fill=hole)

def contours(img, color, seed=3):
    """Decorative topographic lines: clearly abstract, not a map."""
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    cx, cy = W * .72, H * .38
    for k in range(1, 22):
        r = 40 * k; pts = []
        for i in range(181):
            t = i / 180 * 2 * math.pi
            rr = r * (1 + .10 * math.sin(3 * t + k * .35 + seed) + .06 * math.sin(5 * t - k * .2))
            pts.append((cx + rr * math.cos(t), cy + rr * .82 * math.sin(t)))
        d.line(pts, fill=color, width=2)
    img.alpha_composite(lay)

# ---------- A: single spotlight, distance card ----------
def card_single(name, kind, miles):
    img = Image.new("RGBA", (W, H), TAN + (255,))
    contours(img, NAVY + (26,))
    d = ImageDraw.Draw(img)
    img.alpha_composite(logo_tone(GLENS, 300), (W - 300 - 64, 64))
    d.rounded_rectangle([64, 74, 64 + 300, 74 + 52], 26, fill=NAVY)
    d.text((64 + 150, 100), "LOCAL SPOTLIGHT", font=F("b", 22), fill=TAN, anchor="mm")
    # name
    f = F("xb", 96); lines = wrap(d, name, f, W - 128)
    y = 470 - (len(lines) - 1) * 52
    for ln in lines:
        d.text((64, y), ln, font=f, fill=NAVY); y += 104
    d.text((66, y + 14), kind, font=F("m", 40), fill=INK)
    # route line
    ry = 1040; x0, x1 = 120, W - 120
    for x in range(x0 + 30, x1 - 40, 34):
        d.rounded_rectangle([x, ry - 4, x + 18, ry + 4], 4, fill=NAVY)
    d.ellipse([x0 - 22, ry - 22, x0 + 22, ry + 22], fill=GLENS, outline=TAN, width=6)
    pin(d, x1, ry + 22, 30, CORAL, TAN)
    d.text((x0 - 22, ry + 44), "Glens of Bloomfield", font=F("sb", 28), fill=INK)
    d.text((x1 + 22, ry + 44), name.split()[0], font=F("sb", 28), fill=INK, anchor="ra")
    mid = (x0 + x1) / 2; label = f"{miles} mi"
    lw = d.textlength(label, font=F("xb", 44)) + 56
    d.rounded_rectangle([mid - lw / 2, ry - 40, mid + lw / 2, ry + 40], 40, fill=NAVY)
    d.text((mid, ry), label, font=F("xb", 44), fill=TAN, anchor="mm")
    eho(d, NAVY)
    return img.convert("RGB")

# ---------- B: roundup, transit-line list ----------
def card_roundup(title, stops):
    img = Image.new("RGBA", (W, H), NAVY + (255,))
    contours(img, (255, 255, 255, 14), seed=1)
    d = ImageDraw.Draw(img)
    img.alpha_composite(logo_tone((255, 255, 255), 300), (W - 300 - 64, 64))
    d.rounded_rectangle([64, 74, 64 + 300, 74 + 52], 26, fill=TEAL)
    d.text((64 + 150, 100), "LOCAL SPOTLIGHT", font=F("b", 22), fill=NAVY, anchor="mm")
    y = 240
    for ln in wrap(d, title, F("xb", 84), W - 128):
        d.text((64, y), ln, font=F("xb", 84), fill=(255, 255, 255)); y += 92
    x = 120; top = y + 90; gap = 210
    pts = [top + i * gap for i in range(len(stops) + 1)]
    d.line([(x, pts[0]), (x, pts[-1])], fill=TEAL, width=10)
    d.ellipse([x - 26, pts[0] - 26, x + 26, pts[0] + 26], fill=GLENS, outline=(255, 255, 255), width=7)
    d.text((x + 60, pts[0]), "Glens of Bloomfield", font=F("b", 38), fill=(255, 255, 255), anchor="lm")
    for (nm, kind, mi), py in zip(stops, pts[1:]):
        d.ellipse([x - 20, py - 20, x + 20, py + 20], fill=NAVY, outline=TEAL, width=8)
        d.text((x + 60, py - 26), nm, font=F("b", 42), fill=(255, 255, 255), anchor="lm")
        d.text((x + 60, py + 26), kind, font=F("m", 30), fill=(200, 215, 228), anchor="lm")
        lab = f"{mi} mi"; f = F("xb", 34); lw = d.textlength(lab, font=f) + 40
        d.rounded_rectangle([W - 64 - lw, py - 28, W - 64, py + 28], 28, fill=CORAL)
        d.text((W - 64 - lw / 2, py), lab, font=f, fill=NAVY, anchor="mm")
    eho(d, (255, 255, 255))
    return img.convert("RGB")

# ---------- C: property photo with a "nearby" tag ----------
def card_photo(photo, name, kind, miles):
    ph = Image.open(os.path.join(SRC, photo)).convert("RGB")
    bg = ImageOps.fit(ph, (W, H)).filter(ImageFilter.GaussianBlur(40))
    img = Image.new("RGBA", (W, H), NAVY + (255,))
    fg = ImageOps.fit(ph, (W, round(W / 1.5)))
    top = 170; img.paste(fg, (0, top))
    d = ImageDraw.Draw(img)
    img.alpha_composite(logo_tone((255, 255, 255), 280), (W - 280 - 56, 60))
    # nearby band
    by = top + fg.height
    d.rectangle([0, by, W, H], fill=TAN)
    d.rounded_rectangle([64, by + 56, 64 + 260, by + 104], 24, fill=NAVY)
    d.text((64 + 130, by + 80), "JUST NEARBY", font=F("b", 22), fill=TAN, anchor="mm")
    f = F("xb", 64); y = by + 130
    for ln in wrap(d, name, f, W - 128 - 220):
        d.text((64, y), ln, font=f, fill=NAVY); y += 72
    d.text((66, y + 6), kind, font=F("m", 34), fill=INK)
    d.ellipse([W - 64 - 190, by + 120, W - 64, by + 310], fill=CORAL)
    d.text((W - 64 - 95, by + 196), str(miles), font=F("xb", 72), fill=NAVY, anchor="mm")
    d.text((W - 64 - 95, by + 252), "miles", font=F("b", 28), fill=NAVY, anchor="mm")
    eho(d, NAVY)
    return img.convert("RGB")

A = card_single("Madeleine's French Patisserie", "French bakery", 1.2)
B = card_roundup("3 spots near Glens", [("Madeleine's French Patisserie", "Bakery", 1.2), ("Stroh's Ice Cream Parlor", "Ice cream", 1.3), ("Birmingham Bloomfield Art Center", "Arts center", 1.9)])
C = card_photo("4716e88ba0ba94afe865f83cb912c086.jpg", "Madeleine's French Patisserie", "French bakery", 1.2)
for n, im in [("A-distance-card", A), ("B-roundup", B), ("C-photo-nearby", C)]:
    im.save(os.path.join(OUT, n + ".jpg"), quality=90)
# side-by-side sheet
gap = 40; sheet = Image.new("RGB", (W * 3 + gap * 4, H + gap * 2), (230, 230, 230))
for i, im in enumerate([A, B, C]): sheet.paste(im, (gap + i * (W + gap), gap))
sheet.resize((sheet.width // 2, sheet.height // 2), Image.LANCZOS).save(os.path.join(OUT, "local-spotlight-mockups.jpg"), quality=88)
print("ok")
