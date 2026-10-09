"""Band lookup: band name -> Bandcamp page URL (via DuckDuckGo lite), cached.

Cache file: bands_cache.json  {band_lower: url_or_null}
Run this file directly to top up the cache for bands in current events:
    .venv/bin/python bandcamp.py            # fill missing (cap 60/run)
    .venv/bin/python bandcamp.py 200        # custom cap
"""
import json
import re
import time
import requests
from bs4 import BeautifulSoup

CACHE_FILE = "bands_cache.json"
HEADERS = {"User-Agent": "Mozilla/5.0"}

bandcamp_host_re = re.compile(r"^https://([a-z0-9_-]+)\.bandcamp\.com/?[a-z-]*/?$", re.I)


def load_cache():
    try:
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=0, sort_keys=True)


MB_HEADERS = {"User-Agent": "punkshows-app/1.0 (https://punkshows.local)"}


def mb_bandcamp(band):
    """MusicBrainz artist search -> Bandcamp (or official homepage) URL.
    Bot-friendly API; keep >=1 req/sec."""
    try:
        r = requests.get("https://musicbrainz.org/ws/2/artist/",
                         params={"query": band, "fmt": "json", "limit": 5},
                         headers=MB_HEADERS, timeout=15)
        if r.status_code != 200:
            return None
        artists = r.json().get("artists", [])
        if not artists:
            return None
        want = band.strip().lower()
        artist = next((a for a in artists if a["name"].lower() == want), artists[0])
        time.sleep(1.2)
        r2 = requests.get(f"https://musicbrainz.org/ws/2/artist/{artist['id']}",
                          params={"inc": "url-rels", "fmt": "json"},
                          headers=MB_HEADERS, timeout=15)
        if r2.status_code != 200:
            return None
        bandcamp = homepage = None
        for rel in r2.json().get("relations", []):
            u = rel["url"]["resource"]
            if "bandcamp.com" in u:
                bandcamp = bandcamp or u
            elif rel.get("type") == "official homepage":
                homepage = homepage or u
        return bandcamp or homepage
    except requests.RequestException:
        return None


def search_bandcamp(band):
    """MusicBrainz only: DDG lite is permanently bot-blocked from this IP
    (HTTP 202 anomaly page), and its retries cost ~2.5 min per miss."""
    return mb_bandcamp(band)


def ddg_bandcamp(band):
    """DuckDuckGo lite search fallback. Retries on DDG's 202 bot page."""
    q = band.strip() + " bandcamp"
    r = None
    for attempt in range(4):
        try:
            r = requests.post("https://lite.duckduckgo.com/lite/",
                              data={"q": q}, headers=HEADERS, timeout=20)
            if r.status_code == 202:      # anomaly/bot page
                time.sleep(15 * (attempt + 1))
                continue
            r.raise_for_status()
            break
        except requests.RequestException:
            time.sleep(5 * (attempt + 1))
    if r is None or r.status_code == 202:
        return None
    soup = BeautifulSoup(r.text, "html.parser")
    slug = re.sub(r"[^a-z0-9]+", "", band.lower())  # 'hammerfall', 'kobra-thelotus'
    exact, prefix, first, best = None, None, None, None
    for a in soup.find_all("a"):
        href = a.get("href", "")
        m = re.search(r"uddg=([^&]+)", href)
        url = requests.compat.urldecode(m.group(1)) if m else href
        hm = bandcamp_host_re.match(url)
        if hm:
            sub = hm.group(1).lower().replace("-", "")
            if exact is None and sub == slug:
                exact = url
            elif prefix is None and (slug.startswith(sub) or sub.startswith(slug)):
                prefix = url
            elif first is None:
                first = url
        elif best is None and ".bandcamp.com" in url:
            best = url          # album/track page as fallback
    return exact or prefix or first or best


def lookup(band, cache=None):
    """Cached lookup. Returns URL string or None."""
    if cache is None:
        cache = load_cache()
    key = band.strip().lower()
    if key in cache:
        return cache[key]
    url = search_bandcamp(band)
    cache[key] = url
    save_cache(cache)
    return url


def listen_url(band, cache):
    """URL for the 'listen' link: cached Bandcamp page, else a Bandcamp
    search link (works in a browser even though the API is bot-blocked)."""
    key = band.strip().lower()
    url = cache.get(key)
    if url:
        return url
    return "https://bandcamp.com/search?q=" + requests.compat.quote_plus(band.strip())


def split_bands(lineup):
    """Split a lineup string into individual band names (best effort).
    Drops editorial notes in [brackets]/(parens) and 'featuring ...' tails
    (NCS calendars use these for festivals/notes, e.g. 'more TBA)')."""
    if not lineup:
        return []
    lineup = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", lineup)
    lineup = re.sub(r"(?i)\b(featuring|feat\.?)\b.*$", " ", lineup)
    parts = re.split(r",|;|\s\+\s| vs\.? ", lineup)
    return [p.strip() for p in parts if len(p.strip()) > 1]


if __name__ == "__main__":
    import sys
    import sources
    args = sys.argv[1:]
    clear = "clear" in args
    nums = [a for a in args if a.isdigit()]
    cap = int(nums[0]) if nums else 60
    cache = load_cache()
    if clear:
        # drop failed lookups so they get retried (e.g. after a bot-block)
        cache = {k: v for k, v in cache.items() if v}
        save_cache(cache)
    missing = []
    for ev in sources.all_events():
        for b in split_bands(ev["bands"]):
            k = b.lower()
            if k and k not in cache:
                missing.append(b)
    seen, todo = set(), []
    for b in missing:
        if b.lower() not in seen:
            seen.add(b.lower())
            todo.append(b)
    todo = todo[:cap]
    print(f"{len(todo)} bands to look up (of {len(seen)} missing)")
    for i, b in enumerate(todo, 1):
        url = search_bandcamp(b)
        cache[b.lower()] = url
        print(i, b, "->", url)
        save_cache(cache)
