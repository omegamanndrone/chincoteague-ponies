#!/usr/bin/env python
"""scrape_pedigrees.py -- fetch + cache the chincoteaguepedigrees.com source data.

Phase 2, step 1 (IMPLEMENTATION_PLAN.md S6). This script ONLY fetches and caches
raw HTML; parsing lives in parse_pedigree.py. Run it, then iterate the parser
offline against the cache without re-hitting the site.

What it does
------------
1. POST herds.php for all four roster views (VA/MD x Current/Past), cache raw HTML,
   and extract each roster's (id, name, nicknames, sex, color, age) rows.
2. Fetch pedigree.php?id=N for every CURRENT-roster pony (VA 148 + MD 88), cache
   raw HTML. Past pages are NOT fetched -- departed-detection only needs the Past
   roster *id sets*, which the roster step already captures (739 Past pages would
   be a needless hammering of the site).

Polite by default: browser-like headers (else HTTP 406), ~1.6s throttle, and a
resumable on-disk cache (a page already cached is skipped unless --refresh).

  python scrape_pedigrees.py                  # rosters + all current pedigree pages
  python scrape_pedigrees.py --only-rosters   # just the 4 roster lists
  python scrape_pedigrees.py --limit 5        # first 5 current pages (smoke test)
  python scrape_pedigrees.py --refresh        # ignore cache, re-fetch everything
"""
import argparse
import json
import os
import re
import sys
import time

import requests

BASE = "https://chincoteaguepedigrees.com/pedigree/"
HERDS = BASE + "herds.php"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": HERDS,
}

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "scrape")
RAW = os.path.join(OUT, "raw")

ROSTERS = [
    ("Virginia", "Current"),
    ("Virginia", "Past"),
    ("Maryland", "Current"),
    ("Maryland", "Past"),
]


def _slug(state, status):
    return f"roster_{state.lower()}_{status.lower()}"


# A roster row, e.g.:
# <tr class=female2><td><a href=pedigree.php?id=3  target=_blank>A Splash of Freckles</a>
#   (Splash of Freckles)</td><td>female</td><td>bay pinto</td><td>20</td></tr>
ROW_RE = re.compile(
    r"<tr class=(?P<cls>female2|male2|horse2)>"
    r"<td><a href=pedigree\.php\?id=(?P<id>\d+)[^>]*>(?P<name>[^<]+)</a>"
    r"(?P<nick>[^<]*)</td>"
    r"<td>(?P<sex>[^<]*)</td>"
    r"<td>(?P<color>[^<]*)</td>"
    r"<td>(?P<age>[^<]*)</td>",
    re.I,
)


def parse_roster(html):
    rows = []
    for m in ROW_RE.finditer(html):
        nick = m.group("nick").strip()
        nick = nick[1:-1].strip() if nick.startswith("(") and nick.endswith(")") else nick
        nicknames = [n.strip() for n in nick.split(",") if n.strip()] if nick else []
        rows.append({
            "id": int(m.group("id")),
            "name": m.group("name").strip(),
            "nicknames": nicknames,
            "sex": m.group("sex").strip(),
            "color": m.group("color").strip(),
            "age": m.group("age").strip(),
        })
    return rows


def fetch_roster(session, state, status, refresh):
    path = os.path.join(RAW, _slug(state, status) + ".html")
    if os.path.exists(path) and not refresh:
        html = open(path, encoding="utf-8").read()
    else:
        r = session.post(HERDS, headers=HEADERS,
                         data={"state": state, "status": status, "sort": "Name"},
                         timeout=30)
        r.raise_for_status()
        html = r.text
        open(path, "w", encoding="utf-8").write(html)
        time.sleep(1.6)
    rows = parse_roster(html)
    return rows


def fetch_pedigree(session, hid, refresh, delay):
    path = os.path.join(RAW, f"pedigree_{hid}.html")
    if os.path.exists(path) and not refresh:
        return False  # cached, no network hit
    r = session.get(BASE + f"pedigree.php?id={hid}", headers=HEADERS, timeout=30)
    r.raise_for_status()
    open(path, "w", encoding="utf-8").write(r.text)
    time.sleep(delay)
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only-rosters", action="store_true",
                    help="fetch the 4 roster lists, skip pedigree pages")
    ap.add_argument("--limit", type=int, default=0,
                    help="cap how many current pedigree pages to fetch (0 = all)")
    ap.add_argument("--refresh", action="store_true",
                    help="ignore the cache and re-fetch")
    ap.add_argument("--delay", type=float, default=1.6,
                    help="seconds between pedigree fetches (default 1.6)")
    args = ap.parse_args()

    os.makedirs(RAW, exist_ok=True)
    session = requests.Session()

    rosters = {}
    for state, status in ROSTERS:
        rows = fetch_roster(session, state, status, args.refresh)
        rosters[_slug(state, status)] = rows
        print(f"  {state:8} {status:7} {len(rows):4d} ponies")

    summary = {k: [r["id"] for r in v] for k, v in rosters.items()}
    json.dump({"rosters": rosters, "id_sets": summary},
              open(os.path.join(OUT, "rosters.json"), "w", encoding="utf-8"),
              indent=2, ensure_ascii=False)
    print(f"  -> wrote rosters.json")

    if args.only_rosters:
        return

    current_ids = (summary[_slug("Virginia", "Current")] +
                   summary[_slug("Maryland", "Current")])
    if args.limit:
        current_ids = current_ids[:args.limit]

    total = len(current_ids)
    fetched = cached = 0
    print(f"\nFetching {total} current pedigree pages (throttle {args.delay}s, resumable)...")
    for i, hid in enumerate(current_ids, 1):
        try:
            hit = fetch_pedigree(session, hid, args.refresh, args.delay)
        except requests.HTTPError as e:
            print(f"  !! id={hid} HTTP error: {e}")
            continue
        if hit:
            fetched += 1
        else:
            cached += 1
        if i % 25 == 0 or i == total:
            print(f"  {i:4d}/{total}  (network {fetched}, cached {cached})")
    print(f"\nDone. {fetched} fetched, {cached} already cached. Raw HTML in {RAW}")


if __name__ == "__main__":
    main()
