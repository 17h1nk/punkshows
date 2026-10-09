#!/usr/bin/env python3
"""CLI listing of punk/metal shows. Examples:
    ./cli.py                      next 30 days, all genres
    ./cli.py --genre metal        metal only
    ./cli.py --days 7 --city tacoma
    ./cli.py --listen --json      JSON with Bandcamp listen links
"""
import argparse
import datetime
import json
import sys

import bandcamp
import sources as src


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--days", type=int, default=30,
                    help="window from today (0 = everything listed)")
    ap.add_argument("--genre", choices=["all", "punk", "metal"], default="all")
    ap.add_argument("--city", default="", help="substring filter on city/venue")
    ap.add_argument("--listen", action="store_true",
                    help="append Bandcamp listen links per band")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    a = ap.parse_args()

    events = src.filter_area(src.all_events())
    today = datetime.date.today()
    if a.days > 0:
        end = today + datetime.timedelta(days=a.days)
        events = [e for e in events if today <= datetime.date(
            *map(int, e["date"].split("-"))) <= end]
    if a.genre != "all":
        events = [e for e in events if e["genre"] == a.genre]
    if a.city:
        c = a.city.lower()
        events = [e for e in events if c in (e["city"] + " " + e["venue"]).lower()]

    cache = bandcamp.load_cache()

    if a.json:
        out = []
        for e in events:
            row = dict(e)
            if a.listen:
                row["listen"] = {b: bandcamp.listen_url(b, cache)
                                 for b in bandcamp.split_bands(e["bands"])}
            out.append(row)
        print(json.dumps(out, indent=1))
        return

    cur = ""
    for e in events:
        if e["date"] != cur:
            cur = e["date"]
            print(cur + "  " + datetime.date(
                *map(int, cur.split("-"))).strftime("%a"))
        line = f"  [{e['genre'][:1]}] {e['venue'] or '?'} ({e['city'] or '?'})"
        if e["venue"]:
            line += f"  ↗ {src.venue_link(e)}"
        if e["bands"]:
            line += " — " + e["bands"]
        elif e.get("flyer"):
            line += f" — see flyer: {e['flyer']}"
        line += f"  <{e['source']}>"
        print(line)
        if a.listen:
            for b in bandcamp.split_bands(e["bands"]):
                print(f"      ♪ {b}: {bandcamp.listen_url(b, cache)}")
    print(f"\n{len(events)} shows")


if __name__ == "__main__":
    sys.exit(main())
