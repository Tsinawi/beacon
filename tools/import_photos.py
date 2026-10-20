"""Turns the image URLs in a pages.json into new, upload-ready photos.

    python3 tools/import_photos.py out/glens/pages.json out/glens/photos --known known_hashes.txt

- Requests the largest version a known host offers (RentCafe and WordPress sizes are rewritten).
- Drops logos, icons, textures and anything under 700 px wide.
- Drops near-duplicates of each other and of photos already in the library (the
  `hash` field of `media` documents; pass them one per line with --known).
- Writes JPEGs at most 1600 px on the long side plus manifest.json for the upload step.

Photos are kept only when they appear on the community's own pages. A WordPress media
library can hold other properties' images, so it is never read directly.
"""
import argparse
import hashlib
import io
import json
import os
import re
import urllib.parse
import urllib.request

from PIL import Image

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130 Safari/537.36"
SKIP_NAME = re.compile(r"logo|favicon|icon|sprite|marble|texture|pattern|badge|glassdoor|cookielaw|onetrust|housing|eho|placeholder|blank|pixel|map[-_]?pin|istock|adobestock|shutterstock|getty|stock[-_]", re.I)
# Hints for the reviewer; every kept image is still looked at before it is added.
HINTS = [("floorplan", re.compile(r"(^|[^a-z])fp([^a-z]|$)|floor.?plan", re.I)),
         ("flyer", re.compile(r"spec(ial)?[^a-z]|promo|flyer|free|move.?in|concession", re.I))]
MIN_WIDTH = 700


def best_url(url):
    m = re.match(r"(https://resource\.rentcafe\.com/image/upload/)(?:[^/]+/)*?(s3/.+)$", url)
    if m:
        return m.group(1) + "q_auto,f_jpg,c_limit,w_1600/" + m.group(2)
    # WordPress resized copies: name-1024x683.jpg -> name.jpg
    return re.sub(r"-\d{2,4}x\d{2,4}(\.(?:jpe?g|png|webp))$", r"\1", url, flags=re.I)


def dhash(im, size=8):
    g = im.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = (bits << 1) | (px[row * (size + 1) + col] > px[row * (size + 1) + col + 1])
    return f"{bits:016x}"


def distance(a, b):
    return bin(int(a, 16) ^ int(b, 16)).count("1")


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pages")
    ap.add_argument("out")
    ap.add_argument("--known", help="file with one known photo hash per line")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    known = []
    if args.known and os.path.exists(args.known):
        known = [l.strip() for l in open(args.known) if l.strip()]

    pages = json.load(open(args.pages))["pages"]
    urls, seen_urls = [], set()
    for p in pages:
        for u in p.get("images") or []:
            if not re.search(r"\.(jpe?g|png|webp)(\?|$)|/image/upload/", u, re.I):
                continue
            if SKIP_NAME.search(u.split("/")[-1]) or u.lower().endswith(".svg"):
                continue
            b = best_url(u)
            if b not in seen_urls:
                seen_urls.add(b)
                urls.append((b, p.get("url")))

    kept, hashes = [], list(known)
    for url, page in urls:
        try:
            im = Image.open(io.BytesIO(fetch(url)))
            im.load()
            if im.mode in ("P", "LA"):
                im = im.convert("RGBA")
        except Exception as e:  # unreachable or not an image
            print("skip (fetch)", url, e)
            continue
        if im.width < MIN_WIDTH:
            continue
        h = dhash(im)
        dup = next((k for k in hashes if distance(h, k) <= 6), None)
        if dup:
            continue
        hashes.append(h)
        im = im.convert("RGB")
        im.thumbnail((1600, 1600))
        name = f"{len(kept):03d}-{hashlib.sha1(url.encode()).hexdigest()[:8]}.jpg"
        path = os.path.join(args.out, name)
        im.save(path, "JPEG", quality=85, optimize=True)
        source_file = urllib.parse.unquote(url.split("/")[-1].split("?")[0])
        hint = next((k for k, rx in HINTS if rx.search(source_file)), "photo")
        kept.append({"file": os.path.abspath(path), "hash": h, "sourceUrl": url, "page": page, "width": im.width, "height": im.height,
                     "sourceFile": source_file, "hint": hint})
        print("new  ", name, url)

    json.dump(kept, open(os.path.join(args.out, "manifest.json"), "w"), indent=1)
    print(f"{len(kept)} new photos, {len(urls) - len(kept)} skipped as small, duplicate, known or decorative")


if __name__ == "__main__":
    main()
