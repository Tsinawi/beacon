"""Posts approved Beacon Social posts to Facebook Pages and Instagram through Meta's Graph API.

This script never writes content. It posts exactly the approved images and caption, and only
after every safety check passes. It runs in the locked-down publisher environment, where the
AutoPublisher system-user token is added to requests to graph.facebook.com by the network
proxy; the token never appears in this code, its arguments, or its output.

    python3 tools/publish_meta.py verify
    python3 tools/publish_meta.py publish --post post.json --community community.json \
        --control control.json --now 2026-11-20T10:05 --image slide1.jpg [--image slide2.jpg] [--live]

Without --live, publish is a dry run: it runs every check and reports what it would post.
Output is one JSON object on stdout.
"""
import argparse
import datetime
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

GRAPH = "https://graph.facebook.com/v21.0"
NEEDED = {"pages_show_list", "pages_read_engagement", "pages_manage_posts", "instagram_basic", "instagram_content_publish"}


# ---------- Graph API ----------
class GraphError(Exception):
    pass


def call(method, path, params=None, files=None, page_token=None):
    """One Graph API request. The system-user token is added by the proxy; a Page token, when one
    is needed, goes in the form body (never the URL) so it can't land in logs."""
    params = dict(params or {})
    if page_token:
        params["access_token"] = page_token
    url = path if path.startswith("http") else f"{GRAPH}/{path.lstrip('/')}"
    data, headers = None, {"User-Agent": "BeaconSocial/1.0"}
    if method == "GET":
        if params:
            url += "?" + urllib.parse.urlencode(params)
    elif files:
        boundary = uuid.uuid4().hex
        parts = []
        for k, v in params.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
        for k, (name, blob) in files.items():
            parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode() + blob + b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        data = b"".join(parts)
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    else:
        data = urllib.parse.urlencode(params).encode()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            err = json.load(e).get("error", {})
            msg = f"{err.get('type', 'Error')} {err.get('code', '')}: {err.get('message', '')}"
        except Exception:
            msg = f"HTTP {e.code}"
        raise GraphError(msg) from None


# ---------- checks ----------
def canon(v):
    """Matches canon() in the command center, so both sides hash identical text."""
    return json.dumps(v, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def approval_sig(post):
    payload = {
        "v": 1, "communityId": post.get("communityId"), "date": post.get("date"), "time": post.get("time") or "",
        "caption": post.get("caption") or "", "hashtags": post.get("hashtags") or "", "link": post.get("approvedLink") or "",
        "platforms": {k: bool((post.get("platforms") or {}).get(k)) for k in ("facebook", "instagram", "google")},
        "images": post.get("finalAssetIds") or ([post["finalAssetId"]] if post.get("finalAssetId") else []),
    }
    return hashlib.sha256(canon(payload).encode("utf-8")).hexdigest()


def checks(post, community, control, now, images):
    """Every reason not to post. An empty list means it's safe to go."""
    problems = []
    if control.get("paused", True):
        problems.append("publishing is paused")
    if post.get("status") != "approved":
        problems.append(f"status is {post.get('status')!r}, not approved")
    if not control.get("approverId"):
        problems.append("no approver is set in the command center")
    elif post.get("approvedBy") != control["approverId"]:
        problems.append("not approved by the designated approver")
    if not post.get("approvedSig") or post["approvedSig"] != approval_sig(post):
        problems.append("post changed after approval (fingerprint mismatch)")
    when = datetime.datetime.fromisoformat(f"{post['date']}T{post.get('time') or '10:00'}")
    late = (now - when).total_seconds() / 3600
    if late < 0:
        problems.append("not due yet")
    elif late > float(control.get("lateHours", 3)):
        problems.append(f"missed: {late:.1f} hours late, past the {control.get('lateHours', 3)}-hour window")
    if post.get("mediaKind") == "video":
        problems.append("video posts are published by hand for now")
    want = post.get("finalAssetIds") or ([post["finalAssetId"]] if post.get("finalAssetId") else [])
    if len(images) != len(want) or not want:
        problems.append(f"expected {len(want)} approved image(s), got {len(images)}")
    meta = community.get("meta") or {}
    if (post.get("platforms") or {}).get("facebook") and not meta.get("pageId"):
        problems.append("community has no connected Facebook Page")
    if (post.get("platforms") or {}).get("instagram") and not meta.get("igUserId"):
        problems.append("community has no connected Instagram account")
    return problems


def compose(post, platform):
    caption = (post.get("caption") or "").strip()
    tags = (post.get("hashtags") or "").strip()
    link = (post.get("approvedLink") or "").strip()
    parts = [caption]
    if platform == "facebook" and link:
        parts.append(link)
    if tags:
        parts.append(tags)
    return "\n\n".join(p for p in parts if p)


# ---------- posting ----------
def page_token(page_id):
    t = call("GET", page_id, {"fields": "access_token"}).get("access_token")
    if not t:
        raise GraphError("no Page token returned; check the system user's access to this Page")
    return t


def upload_photo(page_id, token, blob, published, caption=None):
    params = {"published": "true" if published else "false"}
    if caption is not None:
        params["caption"] = caption
    return call("POST", f"{page_id}/photos", params, files={"source": ("post.jpg", blob)}, page_token=token)["id"]


def photo_url(photo_id, token):
    imgs = call("GET", photo_id, {"fields": "images"}, page_token=token).get("images") or []
    if not imgs:
        raise GraphError("Facebook returned no image link for the hidden photo")
    return max(imgs, key=lambda i: i.get("width", 0))["source"]


def post_facebook(page_id, token, blobs, message):
    if len(blobs) == 1:
        pid = upload_photo(page_id, token, blobs[0], True, message)
        return {"platform": "facebook", "id": pid}
    ids = [upload_photo(page_id, token, b, False) for b in blobs]
    params = {"message": message}
    for i, mid in enumerate(ids):
        params[f"attached_media[{i}]"] = json.dumps({"media_fbid": mid})
    res = call("POST", f"{page_id}/feed", params, page_token=token)
    return {"platform": "facebook", "id": res["id"]}


def post_instagram(page_id, ig_id, token, blobs, caption):
    # Instagram fetches images by link: upload each as a hidden (unpublished) Page photo and use its link.
    hidden = [upload_photo(page_id, token, b, False) for b in blobs]
    urls = [photo_url(h, token) for h in hidden]
    if len(urls) == 1:
        container = call("POST", f"{ig_id}/media", {"image_url": urls[0], "caption": caption}, page_token=token)["id"]
    else:
        kids = [call("POST", f"{ig_id}/media", {"image_url": u, "is_carousel_item": "true"}, page_token=token)["id"] for u in urls]
        container = call("POST", f"{ig_id}/media", {"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption}, page_token=token)["id"]
    res = call("POST", f"{ig_id}/media_publish", {"creation_id": container}, page_token=token)
    for h in hidden:
        try:
            call("DELETE", h, page_token=token)
        except GraphError:
            pass  # a leftover hidden photo is harmless; it never shows on the Page
    return {"platform": "instagram", "id": res["id"]}


# ---------- commands ----------
def cmd_verify():
    me = call("GET", "me", {"fields": "id,name"})
    perms = call("GET", "me/permissions").get("data", [])
    granted = {p["permission"] for p in perms if p.get("status") == "granted"}
    accounts = call("GET", "me/accounts", {"fields": "id,name,tasks,instagram_business_account{id,username}", "limit": 100}).get("data", [])
    pages = [{"pageId": a["id"], "name": a.get("name"), "tasks": a.get("tasks", []),
              "igUserId": (a.get("instagram_business_account") or {}).get("id"),
              "igUsername": (a.get("instagram_business_account") or {}).get("username")} for a in accounts]
    return {"ok": NEEDED <= granted, "systemUser": me, "missingPermissions": sorted(NEEDED - granted),
            "extraPermissions": sorted(granted - NEEDED), "pages": pages}


def cmd_publish(args):
    post, community, control = (json.load(open(f)) for f in (args.post, args.community, args.control))
    now = datetime.datetime.fromisoformat(args.now)
    blobs = [open(f, "rb").read() for f in args.image]
    problems = checks(post, community, control, now, blobs)
    plats = [p for p in ("facebook", "instagram") if (post.get("platforms") or {}).get(p)]
    out = {"title": post.get("title"), "communityId": post.get("communityId"), "platforms": plats, "problems": problems}
    if problems:
        out["result"] = "skipped" if any(p.startswith(("not due", "missed", "publishing is paused")) for p in problems) else "blocked"
        return out
    if not args.live or control.get("dryRun", True):
        out["result"] = "dry-run"
        out["wouldPost"] = {p: compose(post, p) for p in plats}
        return out
    meta = community["meta"]
    token = page_token(meta["pageId"])
    done, errors = [], []
    for plat in plats:
        try:
            if plat == "facebook":
                done.append(post_facebook(meta["pageId"], token, blobs, compose(post, "facebook")))
            else:
                done.append(post_instagram(meta["pageId"], meta["igUserId"], token, blobs, compose(post, "instagram")))
        except GraphError as e:
            errors.append(f"{plat}: {e}")
    out["posted"] = done
    out["errors"] = errors
    out["result"] = "posted" if done and not errors else "partial" if done else "failed"
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("verify")
    p = sub.add_parser("publish")
    p.add_argument("--post", required=True)
    p.add_argument("--community", required=True)
    p.add_argument("--control", required=True)
    p.add_argument("--now", required=True, help="current local time, America/Detroit, e.g. 2026-11-20T10:05")
    p.add_argument("--image", action="append", default=[])
    p.add_argument("--live", action="store_true")
    args = ap.parse_args()
    try:
        res = cmd_verify() if args.cmd == "verify" else cmd_publish(args)
    except GraphError as e:
        res = {"result": "failed", "error": str(e)}
    json.dump(res, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()
