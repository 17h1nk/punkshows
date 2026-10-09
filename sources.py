"""Scrapers for punk/metal show listings in the Tacoma-Seattle-Olympia area.

Each scraper returns a list of normalized event dicts:
    date       'YYYY-MM-DD' (start)
    date_end   'YYYY-MM-DD' or None (multi-day span)
    venue      venue name ('' if unknown)
    city       best-known city ('' if unknown)
    bands      lineup string ('' if unknown)
    genre      'metal' | 'punk'
    source     source name
    url        source page or event page URL
"""
import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0"}

MONTHS = {
    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
}

# Known venue -> city (extend as needed)
VENUE_CITY = {
    "the kraken": "Seattle",
    "the neptune": "Seattle",
    "neptune": "Seattle",
    "central saloon": "Seattle",
    "the shoebox": "Seattle",
    "the big dipper": "Seattle",
    "el corazon": "Seattle",
    "rickshaw theatre": "Seattle",
    "columbia auditorium": "Seattle",
    "georgetown lodge": "Seattle",
    "funhouse": "Seattle",
    "bar george": "Seattle",
    "the sunken lounge": "Seattle",
    "holocaust": "Seattle",
    "206 lounge": "Seattle",
    "roxy": "Seattle",
    "ballard lodge": "Seattle",
    "hale's palace": "Seattle",
    "pacific science center": "Seattle",
    "zeus zsw": "Seattle",
    "zoo house": "Seattle",
    "lazer loft": "Seattle",
    "the penguin": "Seattle",
    "olympia": "Olympia",
    "capitol city music presents": "Olympia",
    "the 4th of the present": "Olympia",
    "black box": "Olympia",
    "coffee house": "Olympia",
    "the tavern": "Olympia",
    "metropolitan tavern": "Olympia",
    "the space": "Seattle",
    "tacomah": "Tacoma",
    "the dome": "Tacoma",
    "wunderbar": "Tacoma",
    "the little theatre of hammers": "Tacoma",
    "parkland station": "Parkland",
    "the emerald city": "Seattle",
    # seattleareapunkshows.org venues
    "add a ball": "Seattle",
    "clock out lounge": "Seattle",
    "conor byrne pub": "Seattle",
    "rat house": "Seattle",
    "the charleston": "Seattle",
    "baba yaga": "Seattle",
    "belltown yacht club": "Seattle",
    "real art tacoma": "Tacoma",
    "slims last chance": "Seattle",
    "strange ways": "Seattle",
    "the crypt": "Olympia",
    "bayside cafe": "Everett",
    "cha cha": "Seattle",
    "black lodge": "Seattle",
    "the showbox": "Seattle",
    "new frontier lounge": "Seattle",
}

# Cities explicitly outside the Tacoma-Seattle-Olympia area
OUT_OF_AREA = {
    "vancouver bc", "vancouver", "spokane", "portland", "eugene",
    "salem", "bend", "boise", "calgary", "edmonton", "san francisco",
    "los angeles", "new york", "chicago", "denver", "Austin", "philly",
}

# Cities inside our coverage area (lowercase)
AREA_CITIES = {
    "seattle", "tacoma", "olympia", "bellevue", "kent", "renton",
    "everett", "kirkland", "federal way", "puyallup", "bremerton",
    "burien", "edmonds", "lynnwood", "shoreline", "tukwila", "redmond",
    "issaquah", "sammamish", "mercer island", "white center", "auburn",
    "gig harbor", "lakewood", "parkland", "sumner", "bonney lake",
    "orting", "eatonville", "roy", "yelm", "rainier", "high hill",
    "georgetown", "ballard", "fremont", "capitol hill", "queen anne",
    "wallingford", "greenwood", "northgate", "green lake", "ravenna",
    "bryant", "windermere", "la vista", "seward park", "downtown",
    "belltown", "pioneer square", "shoewater", "international district",
    "beacon hill", "mountlake terrace", "view ridge", "shoreline",
    "redondo", "des Moines", "burton", "kenmore", "kennydale",
    "mukilteo", "mount vernon", "snohomish", "woodinville", "novelty",
    "hobart", "vashon", "yeomalt", "ranier",
}

NCS_URL = "https://www.nocleansinging.com/nw-metal-calendar/"
SAP_URL = "https://seattleareapunkshows.org/"
METALGIGS_URL = "https://metalgigs.us/washington-metal-concerts/"


def fetch(url):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.text


def iso(y, m, d):
    return "%04d-%02d-%02d" % (y, m, d)


def guess_city(venue):
    v = venue.strip().lower().removesuffix(".").strip()
    return VENUE_CITY.get(v, "")


def in_area(city):
    """True if city is unknown (keep) or inside our area; False if explicitly outside."""
    if not city:
        return True
    c = city.strip().lower()
    if c in OUT_OF_AREA:
        return False
    return True  # area list is not exhaustive; keep unknown WA-ish cities


# ---------------------------------------------------------------- NCS (metal)

def parse_ncs(html):
    """No Clean Singing PNW metal calendar. Each show is a <p> like
    'SEP 11 at The Kraken: Band, Band' with year headers '2027 FEB'."""
    soup = BeautifulSoup(html, "html.parser")
    events = []
    year = None
    m = re.search(r"Last updated on\s+(\d{1,2})/(\d{1,2})/(\d{2})", html)
    if m:
        year = 2000 + int(m.group(3))
    if year is None:
        import datetime
        year = datetime.date.today().year

    show_re = re.compile(
        r"^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)"
        r"\s+(\d{1,2})"
        r"(?:\s*(?:[–-]|&|and)\s*(\d{1,2}))?"
        r"\s+at\s+(.+?):\s+(.+)$", re.S)
    header_re = re.compile(r"^(\d{4})\s+(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)$")

    for p in soup.find_all("p"):
        line = p.get_text(" ", strip=True)
        if not line:
            continue
        h = header_re.match(line)
        if h:
            year = int(h.group(1))
            continue
        sm = show_re.match(line)
        if not sm:
            continue
        mon = MONTHS[sm.group(1)]
        d1 = int(sm.group(2))
        d2 = int(sm.group(3)) if sm.group(3) else None
        venue = sm.group(4).strip()
        bands = sm.group(5).strip()
        city = ""
        vm = re.search(r"\(([^)]+)\)\s*$", venue)
        if vm:
            city = vm.group(1).strip()
            venue = venue[: vm.start()].strip()
        date_end = iso(year, mon, d2) if d2 and d2 > d1 else None
        events.append({
            "date": iso(year, mon, d1),
            "date_end": date_end,
            "venue": venue,
            "city": city or "Seattle",  # NCS: "Unless otherwise noted, in Seattle"
            "bands": bands,
            "genre": "metal",
            "source": "No Clean Singing",
            "url": NCS_URL,
        })
    return events


# ------------------------------------------------- seattleareapunkshows (punk)

def parse_sap(html):
    """Flyer wall: <img src='images/10.09.26 at Central Saloon.jpg'> etc.
    Filename = MM.DD.YY [at Venue] [Bands].jpg, optional ' (1)' dup suffix."""
    soup = BeautifulSoup(html, "html.parser")
    events = []
    seen = set()
    img_re = re.compile(r"images/(\d{2})\.(\d{2})\.(\d{2})\s+(.+?)\.jpg$")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        m = img_re.search(src)
        if not m:
            continue
        mm, dd, yy = int(m.group(1)), int(m.group(2)), 2000 + int(m.group(3))
        rest = m.group(4).strip()
        rest = re.sub(r"\s*\(\d+\)\s*$", "", rest)  # drop ' (1)' dup suffix
        venue, bands = "", rest
        if rest.lower().startswith("at "):
            venue, bands = rest[3:].strip(), ""
        if bands.lower() in {"sb", "sp", ""}:  # junk filenames
            bands = ""
        if not venue and not bands:
            continue
        key = (iso(yy, mm, dd), venue, bands)
        if key in seen:
            continue
        seen.add(key)
        city = guess_city(venue)
        flyer = SAP_URL + "images/" + src.split("images/", 1)[1]
        events.append({
            "date": iso(yy, mm, dd),
            "date_end": None,
            "venue": venue,
            "city": city,
            "bands": bands,
            "genre": "punk",
            "source": "seattleareapunkshows.org",
            "url": SAP_URL,
            "flyer": flyer,
        })
    return events


# ------------------------------------------------------------ thecryptbar.com

CRYPT_URL = "https://www.thecryptbar.com/"

def parse_crypt(html):
    """Wix events list: each <li> holds 'Fri, Oct 09 BANDS / DETAILS' anchor
    to /events/<slug> plus 'Oct 09, 2026, 7:30 PM'. Drag/strip nights skipped."""
    soup = BeautifulSoup(html, "html.parser")
    events = []
    for li in soup.find_all("li"):
        a = li.find("a", href=re.compile(r"/events/[^/]+"))
        if not a:
            continue
        text = li.get_text(" ", strip=True)
        m = re.search(r"([A-Z][a-z]{2}) (\d{2}), (\d{4})", text)
        if not m:
            continue
        title = re.search(r"^[A-Z][a-z]{2}, ([A-Z][a-z]{2}) (\d{2}) (.*?)(?: / DETAILS|$)", text)
        bands = (title.group(3) if title else "").strip()
        bands = re.sub(r"[\s/]+$", "", bands)          # drop trailing "//"
        bands = re.sub(r"\s{2,}", " ", bands)
        if not bands:
            continue
        low = bands.lower()
        if "drag" in low or "strip at the crypt" in low:
            continue
        slug = a["href"].rstrip("/").rsplit("/", 1)[-1]
        events.append({
            "date": iso(int(m.group(3)), MONTHS[m.group(1).upper()], int(m.group(2))),
            "date_end": None,
            "venue": "The Crypt",
            "city": "Olympia",
            "bands": bands,
            "genre": "metal",
            "source": "thecryptbar.com",
            "url": CRYPT_URL + "events/" + slug,
        })
    return events


# ------------------------------------------------------------- metalgigs (metal)

def parse_metalgigs(html):
    """WordPress EventOn: one JSON-LD Event per event.
    startDate '2026-10-8T20:00-4:00' (date part only), venue in description <p>."""
    events = []
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>', html, re.S
    ):
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for ev in items:
            if not isinstance(ev, dict) or ev.get("@type") != "Event":
                continue
            sd = ev.get("startDate", "")
            dm = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", sd)
            if not dm:
                continue
            desc = ev.get("description", "")
            venue = BeautifulSoup(desc, "html.parser").get_text(" ", strip=True)
            city = guess_city(venue)
            events.append({
                "date": iso(*map(int, dm.groups())),
                "date_end": None,
                "venue": venue,
                "city": city,
                "bands": ev.get("name", "").strip(),
                "genre": "metal",
                "source": "metalgigs.us",
                "url": ev.get("url", METALGIGS_URL),
            })
    return events


# --------------------------------------------------------------------- combine

def all_events():
    """Fetch every source, return combined list sorted by date."""
    events = []
    for fetch_parse in (
        (NCS_URL, parse_ncs),
        (SAP_URL, parse_sap),
        (CRYPT_URL, parse_crypt),
        (METALGIGS_URL, parse_metalgigs),
    ):
        try:
            events += fetch_parse[1](fetch(fetch_parse[0]))
        except Exception as e:
            print("WARN: source failed:", fetch_parse[0], e)
    events.sort(key=lambda e: (e["date"], e["venue"]))
    return events


def filter_area(events):
    return [e for e in events if in_area(e["city"])]


# Official venue websites (verified 2026-10-09; see missingvenues.txt for the venues that
# have none - those keep the Google Maps fallback). Keys are canonical names.
VENUE_SITE = {
    "airport tavern": "https://airporttavern.com/",
    "belltown yacht club": "http://bycseattle.com",
    "baba yaga": "https://babayagaseattle.com/",
    "black lodge": "https://theveraproject.org/blacklodge/",
    "black market skate shop": "https://www.blackmarketskates.com/",
    "blue moon": "https://www.thebluemoonseattle.com/",
    "capitol theater": "https://capitoltheatre.com/",
    "central saloon": "https://centralsaloon.com/",
    "lumen field": "https://www.lumenfield.com/",
    "climate pledge arena": "https://climatepledgearena.com/",
    "clock out lounge": "https://clockoutlounge.com/",
    "conor byrne pub": "https://www.conorbyrnepub.com/",
    "el corazon": "https://www.elcorazonseattle.com/",
    "fox theater": "https://foxtheaterspokane.org/",
    "gasworks park": "https://www.seattle.gov/parks/parks/gas-works-park",
    "highline": "https://www.highlineseattle.com/",
    "knitting factory": "https://www.knittingfactory.com/",
    "kraken bar": "https://thekrakenbar.com/",
    "lucky dime": "https://www.luckydimewa.com/",
    "lucky liquor": "https://www.luckyliquor.online/",
    "makeshift": "https://www.makeshiftartbar.net/",
    "mccoy's firehouse": "https://mccoysfirehouse.com/",
    "midtown ballroom": "https://midtownballroom.com/",
    "moore theatre": "https://www.stgpresents.org/stg-venues/moore-theatre/",
    "nectar lounge": "https://nectarlounge.com/",
    "neptune theatre": "https://www.stgpresents.org/stg-venues/neptune-theatre/",
    "neumos": "https://www.neumos.com/",
    "new frontier lounge": "https://www.newfrontierlounge.com/",
    "northern quest": "https://www.northernquest.com",
    "numerica veterans arena": "https://numericaarena.com/",
    "orient express": "https://orientexpresslounge.com/",
    "paramount theatre": "https://www.stgpresents.org/stg-venues/paramount-theatre/",
    "real art tacoma": "https://www.realarttacoma.com/",
    "redwood theater": "https://redwoodtheater.com/",
    "grand theatre": "https://grandtheatre.com/",
    "showare center": "https://www.accessoshowarecenter.com/",
    "showbox": "https://www.showboxpresents.com/",
    "silver moon brewing": "https://www.silvermoonbrewing.com/",
    "skylark cafe": "https://www.skylarkcafe.com/",
    "slims last chance": "https://www.slimslastchance.com/",
    "south gate roller rink": "http://www.southgaterollerrink.com/",
    "studio seven": "https://www.studio7.com/",
    "substation": "https://substationseattle.com/",
    "sunset tavern": "https://sunsettavern.com/",
    "tacoma dome": "https://www.tacomadome.org/",
    "temple theatre": "https://templetheatre.com/",
    "the big dipper": "https://thebigdipperspokane.com/",
    "the charleston": "https://thecharleston333.com/",
    "the clubhouse": "https://www.theclubhouseseries.com/",
    "the crocodile": "https://www.thecrocodile.com/",
    "the crypt": "https://www.thecryptbar.com/",
    "the mortuary": "https://themortuary.com/",
    "the mountain room": "https://www.themountainroomseattle.com/",
    "the paramount": "https://www.stgpresents.org/stg-venues/paramount-theatre/",
    "the vera project": "https://theveraproject.org/",
    "the voyeur": "https://www.thevoyeur.com/",
    "the yard": "https://theyardcafe.com/",
    "tractor tavern": "https://tractortavern.com/",
    "tracyton movie house": "https://www.tracytonmoviehouse.com/",
    "two fingers social": "https://www.2fingerssocial.com/",
    "wamu theater": "https://www.wamutheater.com/",
    "yakima maker space": "https://yakimamakerspace.org/",
}

# Spelling variants in the data -> canonical key used in VENUE_SITE.
VENUE_ALIAS = {
    "addaball": "add a ball",
    "byc": "belltown yacht club",
    "centurylink field": "lumen field",
    "clock-out lounge": "clock out lounge",
    "the clock out lounge": "clock out lounge",
    "funhouse": "el corazon",          # Funhouse is now run by El Corazon
    "the funhouse": "el corazon",
    "kraken bar": "kraken bar",
    "the kraken": "kraken bar",
    "moore theater": "moore theatre",
    "the moore": "moore theatre",
    "the moore theatre": "moore theatre",
    "neptune": "neptune theatre",
    "the neptune": "neptune theatre",
    "the neptune theatre": "neptune theatre",
    "paramount theatre": "paramount theatre",
    "the paramount": "paramount theatre",
    "showbox sodo": "showbox",
    "the showbox sodo": "showbox",
    "the showbox": "showbox",
    "showbox at market": "showbox",
    "the showbox market": "showbox",
    "vera project": "the vera project",
    "real art": "real art tacoma",
    "black market": "black market skate shop",
    "outer orbit arcade": "outer orbit",
    "substation seattle": "substation",
    "capitol theatre": "capitol theater",
    "capitol backstage": "capitol theater",   # room inside the Capitol Theater
    "mccoys": "mccoy's firehouse",
    "pend oreille pavilion at northern quest": "northern quest",
    "northern quest resort & casino": "northern quest",
    "salem’s historic grand theatre": "grand theatre",
}

# Flyer-filename junk that is not a venue at all -> no link.
NOT_A_VENUE = {"sb", "sp", "qfc", "in tacoma", "guests"}


def venue_link(e):
    """Link for a venue: known official site, else Google Maps search."""
    import urllib.parse
    v = (e["venue"] or "").strip()
    if not v:
        return ""
    key = v.lower()
    if key in NOT_A_VENUE:
        return ""
    site = VENUE_SITE.get(VENUE_ALIAS.get(key, key))
    if site:
        return site
    q = urllib.parse.quote_plus(f'{v} {e["city"] or "Seattle, WA"}')
    return f"https://www.google.com/maps/search/?api=1&query={q}"


if __name__ == "__main__":
    evs = filter_area(all_events())
    print(len(evs), "events")
    for e in evs[:10]:
        print(e["date"], e["genre"], "|", e["venue"] or "?", "|",
              e["city"] or "?", "|", e["bands"] or "?", "|", e["source"])
