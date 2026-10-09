#!/usr/bin/env python3
"""Dark web UI for punk/metal shows. Run:
    .venv/bin/python webapp.py            # http://127.0.0.1:8000
Serves a dark, mobile-friendly page; installable on Android as a PWA
(manifest.webmanifest + icon served; open http://<LAN-IP>:8000 on your
phone's Chrome and tap 'Add to Home Screen'... Chrome needs https for
the official install prompt, so also see snapshot.py for a file you can
copy to any device).
"""
import datetime
import os
import re
import io

from flask import Flask, Response, jsonify, make_response, send_file, abort

import sources as src
import bandcamp
from PIL import Image

CACHE_SECONDS = 600
app = Flask(__name__)
_cache = {"t": 0.0, "events": []}

THUMB_DIR = "thumbs"
THUMB_W = 240


def thumb_name(url):
    return url.rsplit("/", 1)[-1].split("?")[0]


def make_thumb(url):
    """Fetch flyer image, resize to width THUMB_W, cache under THUMB_DIR.
    Returns thumb filename or None."""
    name = thumb_name(url)
    path = os.path.join(THUMB_DIR, name)
    if os.path.exists(path):
        return name
    try:
        r = requests_get(url)
        if r is None or r.status_code != 200:
            return None
        im = Image.open(io.BytesIO(r.content)).convert("RGB")
        os.makedirs(THUMB_DIR, exist_ok=True)
        im.thumbnail((THUMB_W, THUMB_W * 4))
        im.save(path, "JPEG", quality=70)
        return name
    except Exception:
        return None


def requests_get(url):
    import requests
    try:
        return requests.get(url, headers=src.HEADERS, timeout=25)
    except requests.RequestException:
        return None

CSS = """
:root{color-scheme:dark}
*{box-sizing:border-box}
body{background:#111;color:#ddd;font-family:system-ui;margin:0;padding:12px}
a{color:#7ab8ff;text-decoration:none}
h1{font-size:1.3em}
.day{margin-top:1.2em}
.day h2{font-size:1.05em;color:#eee}
.show{margin:.5em 0;padding:.5em .7em;background:#1b1b1b;border-radius:6px}
.meta{font-size:.8em;color:#888}
.band{white-space:normal}
.listen{font-size:.85em}
.badge{display:inline-block;padding:.1em .5em;border-radius:4px;font-size:.75em}
.badge.p{background:#7f1d1d;color:#fff}
.badge.m{background:#3d3d55;color:#fff}
.flyer{display:block;margin:.6em auto .2em;text-align:center}
.thumb{display:block;width:110px;height:auto;margin:auto;border-radius:3px;border:1px solid #333}
"""

ICON = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 192 192'>"
    "<rect width='192' height='192' rx='28' fill='#111'/>"
    "<text x='96' y='128' font-size='120' text-anchor='middle' "
    "font-family='system-ui' fill='#7ab8ff'>?</text></svg>"
)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def refresh():
    import time
    now = time.monotonic()
    if now - _cache["t"] > CACHE_SECONDS:
        _cache["events"] = src.filter_area(src.all_events())
        _cache["t"] = now
    return _cache["events"]


def render_page():
    today = datetime.date.today()
    events = [e for e in refresh()
              if datetime.date(*map(int, e["date"].split("-"))) >= today]
    cache = bandcamp.load_cache()
    days = {}
    for e in events:
        days.setdefault(e["date"], []).append(e)

    out = ['<div class="day"><h2>', ]
    html = []
    for date in sorted(days):
        d = datetime.date(*map(int, date.split("-")))
        html.append(f'<div class="day"><h2>{d.strftime("%a %b %-d")}</h2>')
        for e in days[date]:
            g = e["genre"][0]
            bands_html = esc(e["bands"]) if e["bands"] else ""
            flyer_html = ""
            if e.get("flyer"):
                name = make_thumb(e["flyer"])
                inner = (f'<img class="thumb" loading="lazy" '
                         f'src="/thumbs/{esc(name)}" alt="flyer thumbnail">'
                         if name else "&#128473; flyer")
                flyer_html = f'<div class="flyer"><a href="{esc(e["flyer"])}">{inner}</a></div>'
            listen = []
            for b in bandcamp.split_bands(e["bands"]):
                listen.append(
                    f'<a class="listen" href="{esc(bandcamp.listen_url(b, cache))}">'
                    f"♪ {esc(b)}</a>")
            venue_txt = esc(e["venue"] or "?") + (
                " (" + esc(e["city"]) + ")" if e["city"] else "")
            venue_html = (f'<a class="venue" href="{esc(src.venue_link(e))}">'
                          f'{venue_txt}</a>' if e["venue"] else
                          f'<span class="band">{venue_txt}</span>')
            html.append(
                '<div class="show">'
                f'<span class="badge {g}">{e["genre"]}</span> '
                + venue_html
                + (f' &mdash; <span class="band">{bands_html}</span>' if bands_html else "")
                + flyer_html
                + ("".join(listen) and "<br>" + " ".join(listen))
                + f'<div class="meta">{esc(e["source"])}'
                + (f' &middot; <a href="{esc(e["url"])}">link</a>'
                   if e["url"] != src.NCS_URL and e["url"] != src.SAP_URL else "")
                + "</div></div>")
        html.append("</div>")
    return "".join(html), len(events)


@app.route("/")
def index():
    body, n = render_page()
    today = datetime.date.today()
    page = f"""<!doctype html><meta name=viewport content='width=device-width'>
<link rel=manifest href='/manifest.webmanifest'>
<link rel=icon href='/icon.svg'>
<title>punk + metal shows</title>
<style>{CSS}</style>
<h1>Punk + metal shows &middot; {today.strftime('%b %-d')} onward</h1>
{body}
<div class=meta>sources: No Clean Singing, seattleareapunkshows.org, metalgigs.us
&middot; SAP socials: <a href="https://www.instagram.com/seattleareapunkshowsss">IG</a>
&middot; <a href="https://bsky.app/profile/sapspresents.bsky.social">Bluesky</a>
&middot; <a href="https://www.Tumblr.com/seattleareapunkshows">Tumblr</a>
&middot; refreshes every 10 min &middot; {n} shows upcoming</div>"""
    return Response(page, mimetype="text/html")


@app.route("/manifest.webmanifest")
def manifest():
    return jsonify({
        "name": "punk + metal shows",
        "start_url": "/",
        "display": "minimal",
        "background_color": "#111111",
        "theme_color": "#111111",
        "icons": [{"src": "/icon.svg", "sizes": "any", "type": "image/svg+xml"}],
    })


@app.route("/icon.svg")
def icon():
    return Response(ICON, mimetype="image/svg+xml")


@app.route("/thumbs/<path:name>")
def thumbs(name):
    p = os.path.join(THUMB_DIR, name)
    if not os.path.isfile(p):
        abort(404)
    return send_file(p, mimetype="image/jpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
