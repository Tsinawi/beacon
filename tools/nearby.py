"""Finds named places near a community from OpenStreetMap, for local spotlight posts.

    python3 tools/nearby.py "7480 Bingham Rd, Bloomfield Hills, MI 48301" out/glens/area.json --name "Glens of Bloomfield"

The community is located by name first (OpenStreetMap often knows apartment communities),
then by address. If both miss, pass --lat and --lon.

Uses the OpenStreetMap Nominatim search (one request a second, per its usage policy).
Distances are straight-line miles from the community. Schools, places of worship and
childcare are never collected: posts must not point to them (fair housing).

Data © OpenStreetMap contributors, ODbL 1.0 (https://www.openstreetmap.org/copyright).
"""
import argparse
import datetime
import re
import json
import math
import time
import urllib.parse
import urllib.request

UA = "BeaconSocial/1.0 (apartment community marketing; github.com/Tsinawi/beacon)"
SEARCH = "https://nominatim.openstreetmap.org/search"

# label -> search phrases (Nominatim special phrases)
CATEGORIES = [
    ("Parks & nature", ["park", "nature reserve", "garden"]),
    ("Trails", ["trail", "trailhead"]),
    ("Coffee & bakeries", ["cafe", "bakery"]),
    ("Restaurants", ["restaurant"]),
    ("Treats", ["ice cream", "dessert"]),
    ("Breweries & wine", ["brewery", "winery", "pub"]),
    ("Groceries & markets", ["supermarket", "marketplace", "farmers market"]),
    ("Shopping", ["mall", "department store", "shopping centre"]),
    ("Arts & entertainment", ["cinema", "theatre", "museum", "arts centre"]),
    ("Recreation", ["golf course", "sports centre", "ice rink", "bowling alley", "swimming pool"]),
    ("Libraries", ["library"]),
]
NEVER = {"school", "college", "university", "kindergarten", "childcare", "place_of_worship", "church",
         "mosque", "synagogue", "temple", "grave_yard", "cemetery", "prison", "social_facility"}
# Names that point at children, schools, worship or private clubs, or that would trip the fair housing check.
NAME_SKIP = re.compile(r"school|academy|preschool|daycare|day care|kids|child|famil|church|chapel|ministr|country club|members|razed|closed|former", re.I)
PUBLIC_LIBRARY = re.compile(r"public|district|branch|township|city|county", re.I)
TIDY = re.compile(r"\s+(parking lot|parking|lot)$", re.I)
last_call = [0.0]


def get(params):
    wait = 1.1 - (time.time() - last_call[0])
    if wait > 0:
        time.sleep(wait)
    url = SEARCH + "?" + urllib.parse.urlencode({**params, "format": "jsonv2"})
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    finally:
        last_call[0] = time.time()


def miles(a_lat, a_lon, b_lat, b_lon):
    r = 3958.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def geocode(address, name=None):
    """A precise street-address match wins. Otherwise try the community name, but accept it only
    within 8 miles of wherever the address landed (a town), so a same-named place in another
    state is never used."""
    hits = get({"q": address, "limit": 3, "countrycodes": "us"})
    precise = [h for h in hits if h.get("addresstype") in ("house", "building", "place", "residential", "road")]
    if precise:
        return float(precise[0]["lat"]), float(precise[0]["lon"]), precise[0].get("display_name", "")
    if not hits and "," in address:
        hits = get({"q": address.split(",", 1)[1].strip(), "limit": 1, "countrycodes": "us"})  # the town alone
    if name and hits:
        a_lat, a_lon = float(hits[0]["lat"]), float(hits[0]["lon"])
        state = address.rsplit(",", 1)[-1].strip().split(" ")[0]
        for h in get({"q": f"{name}, {state}", "limit": 5, "countrycodes": "us"}):
            if miles(a_lat, a_lon, float(h["lat"]), float(h["lon"])) <= 8:
                return float(h["lat"]), float(h["lon"]), h.get("display_name", "")
    raise SystemExit(f"could not place {address!r} precisely; pass --lat and --lon")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("address")
    ap.add_argument("out")
    ap.add_argument("--miles", type=float, default=5.0)
    ap.add_argument("--per-category", type=int, default=6)
    ap.add_argument("--name", help="community name, tried before the address")
    ap.add_argument("--lat", type=float)
    ap.add_argument("--lon", type=float)
    args = ap.parse_args()

    if args.lat is not None and args.lon is not None:
        lat, lon, found = args.lat, args.lon, "pinned"
    else:
        lat, lon, found = geocode(args.address, args.name)
    dlat = args.miles / 69.0
    dlon = args.miles / (69.0 * math.cos(math.radians(lat)))
    viewbox = f"{lon - dlon},{lat + dlat},{lon + dlon},{lat - dlat}"

    places = []
    for label, phrases in CATEGORIES:
        best = {}
        for phrase in phrases:
            try:
                hits = get({"q": phrase, "viewbox": viewbox, "bounded": 1, "limit": 20, "countrycodes": "us"})
            except Exception as e:  # keep going; one failed phrase shouldn't sink the run
                print("skip", phrase, e)
                continue
            for h in hits:
                name = TIDY.sub("", (h.get("name") or "").strip())
                kind = h.get("type") or ""
                if not name or kind in NEVER or h.get("category") in NEVER or NAME_SKIP.search(name):
                    continue
                if label == "Recreation" and re.search(r"\bclub\b", name, re.I):
                    continue  # usually members-only
                if label == "Libraries" and not PUBLIC_LIBRARY.search(name):
                    continue  # campus and private libraries
                d = miles(lat, lon, float(h["lat"]), float(h["lon"]))
                if d > args.miles:
                    continue
                key = name.lower()
                if key not in best or d < best[key]["miles"]:
                    best[key] = {"name": name, "category": label, "type": kind.replace("_", " "), "miles": round(d, 1),
                                 "osm": f"https://www.openstreetmap.org/{h.get('osm_type')}/{h.get('osm_id')}"}
        chosen = sorted(best.values(), key=lambda x: x["miles"])[: args.per_category]
        places += chosen
        print(f"{label:22} {len(chosen)}  " + ", ".join(f"{p['name']} ({p['miles']} mi)" for p in chosen[:4]))

    out = {"source": "OpenStreetMap", "attribution": "© OpenStreetMap contributors", "fetchedAt": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "center": {"lat": round(lat, 5), "lon": round(lon, 5), "matched": found}, "radiusMiles": args.miles, "places": places}
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"{len(places)} places saved to {args.out}")


if __name__ == "__main__":
    main()
