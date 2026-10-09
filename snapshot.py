#!/usr/bin/env python3
"""Generate shows.html: one self-contained dark HTML file (works offline,
easy to copy to a phone). Re-scrapes at generation time."""
import datetime
import json
import re
import webapp  # reuse the renderer


def pwa_files():
    """Write manifest.webmanifest + icon.svg next to index.html so the
    Pages-hosted page is installable as a PWA. Paths are relative so they
    resolve under the /punkshows/ subpath (start_url "/" would hit the
    GitHub Pages root instead)."""
    manifest = {
        "name": "punk + metal shows",
        "short_name": "shows",
        "start_url": "./",
        "display": "minimal",
        "background_color": "#111111",
        "theme_color": "#111111",
        "icons": [{"src": "icon.svg", "sizes": "any",
                   "type": "image/svg+xml"}],
    }
    with open("manifest.webmanifest", "w", encoding="utf-8") as f:
        json.dump(manifest, f)
    with open("icon.svg", "w", encoding="utf-8") as f:
        f.write(webapp.ICON)


def inline_thumbs(body):
    """Replace /thumbs/x.jpg src refs with base64 data URIs so the
    snapshot works offline."""
    def repl(m):
        name = m.group(1)
        path = webapp.THUMB_DIR + "/" + name
        try:
            with open(path, "rb") as f:
                from base64 import b64encode
                return 'src="data:image/jpeg;base64,' + b64encode(f.read()).decode() + '"'
        except OSError:
            return m.group(0)
    return re.sub(r'src="/thumbs/([^"]+)"', repl, body)


def web_body(body):
    """Keep /thumbs/ refs but make them relative, for hosting on a project page."""
    return body.replace('src="/thumbs/', 'src="thumbs/')


def main(web=False):
    body, n = webapp.render_page()
    out, title, body = ("index.html", "punk + metal shows", web_body(body)) if web \
        else ("shows.html", "punk + metal shows (snapshot)", inline_thumbs(body))
    today = datetime.date.today()
    links = ("<link rel=icon href='icon.svg'>"
             "<link rel=manifest href='manifest.webmanifest'>") if web else ""
    page = f"""<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>
<title>{title}</title>
{links}
<style>{webapp.CSS}</style>
<h1>Punk + metal shows &middot; {today.strftime('%b %-d')}</h1>
{body}
<div class=meta>generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}
&middot; sources: No Clean Singing, seattleareapunkshows.org, metalgigs.us
&middot; SAP socials: <a href="https://www.instagram.com/seattleareapunkshowsss">IG</a>
&middot; <a href="https://bsky.app/profile/sapspresents.bsky.social">Bluesky</a>
&middot; <a href="https://www.Tumblr.com/seattleareapunkshows">Tumblr</a>
&middot; {n} shows upcoming</div>"""
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    if web:
        pwa_files()
    print("wrote", out, ",", n, "shows")


if __name__ == "__main__":
    import sys
    main(web="--web" in sys.argv)
