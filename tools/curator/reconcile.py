#!/usr/bin/env python
"""reconcile.py -- compare scraped/parsed data against the current app data.

Validation aid for Phase 2 (not part of the ship pipeline). For the horses that
exist in BOTH the current app (horses.db, the 143) and the scrape, it diffs every
shared field and buckets each into:
  same      - identical after normalization
  spelling  - differ only by spelling/case/punctuation (website is now canonical)
  CONFLICT  - a genuine value difference a human should look at
It also reports coverage of the NEW (proposed) fields the scrape adds, and a
terminology section surfacing prose-vs-roster term mismatches (e.g. tobiano/pinto)
so we can build the normalization map from real data.

Three color sources are compared deliberately:
  book color  (horses.db)      e.g. 'Bay Pinto'
  roster color (herds.php cols) e.g. 'bay pinto'      <- proposed canonical (common usage)
  prose color+pattern          e.g. 'Bay' + 'tobiano' <- technical, needs normalizing

  python reconcile.py            # full report
  python reconcile.py --field color   # dump every row for one field
"""
import argparse
import json
import os
import re
import sqlite3
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "scrape")
DB = os.path.normpath(os.path.join(HERE, "..", "..", "horses.db"))

# draft normalization map (prose term -> common usage). Confirm/extend with the user.
PATTERN_NORM = {"tobiano": "pinto"}


def norm(s):
    s = (s or "").lower().strip()
    words = {"fifteen": "15", "twelve": "12", "eleven": "11", "ten": "10", "two": "2"}
    for w, d in words.items():
        s = re.sub(r"\b" + w + r"\b", d, s)
    s = s.replace("&", "and")
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def load():
    recs = {int(k): v for k, v in json.load(open(os.path.join(OUT, "parsed.json"), encoding="utf-8")).items()}
    ros = json.load(open(os.path.join(OUT, "rosters.json"), encoding="utf-8"))
    roster = {}
    for rows in ros["rosters"].values():
        for r in rows:
            roster.setdefault(r["id"], r)  # first wins (current before past)
    book = {}
    c = sqlite3.connect(DB)
    cols = "qr_pedigree_url,name,color,sex,birth_year,eye_color,auction_price,buyback_donor,sire,dam,brand"
    for row in c.execute(f"select {cols} from horses"):
        m = re.search(r"id=(\d+)", row[0] or "")
        if m:
            book[int(m.group(1))] = dict(zip(cols.split(",")[1:], row[1:]))
    return recs, roster, book


def bucket(book_val, new_val):
    if not book_val and not new_val:
        return None
    if not book_val or not new_val:
        return "new-only" if new_val else "book-only"
    a, b = norm(book_val), norm(new_val)
    if a == b:
        return "same"
    if a in b or b in a:
        return "spelling"
    return "CONFLICT"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--field", help="dump every overlapping row for one field")
    args = ap.parse_args()

    recs, roster, book = load()
    common = sorted(set(book) & set(recs))
    print(f"{len(common)} horses present in both app and scrape "
          f"({len(book)} app, {len(recs)} scraped).\n")

    # sex needs canonical mapping book(mare/stallion) <-> site(female/male)
    def sexn(s):
        s = (s or "").lower()
        return "f" if s in ("mare", "female", "filly") else "m" if s in ("stallion", "male", "gelding", "colt") else s

    # nicknames of a parent (by ped id) -- the book often stored a parent by its
    # call-name, which the website carries as a nickname of the formal name.
    def parent_nicks(pid):
        return [n for n in (roster.get(pid, {}).get("nicknames") or [])]

    # --- shared fields: book vs the proposed canonical scrape value ---
    # 4th element (optional): given a foal id, return the parent ped id whose
    # nicknames a name-CONFLICT should be checked against (reclassifies to "alias").
    print("=== SHARED FIELDS: app value vs scrape value (canonical source noted) ===")
    fieldmap = [
        ("color  (<- roster)", lambda h: book[h].get("color"), lambda h: roster.get(h, {}).get("color"), None),
        ("sex",                lambda h: sexn(book[h].get("sex")), lambda h: sexn(recs[h].get("sex")), None),
        ("birth_year",         lambda h: book[h].get("birth_year"), lambda h: recs[h].get("birth_year"), None),
        ("eye_color",          lambda h: book[h].get("eye_color"), lambda h: recs[h].get("eye_color"), None),
        ("auction_price",      lambda h: re.sub(r"[^\d]", "", book[h].get("auction_price") or ""), lambda h: recs[h].get("auction_price"), None),
        ("buyback_donor",      lambda h: book[h].get("buyback_donor"), lambda h: recs[h].get("buyback_donor"), None),
        ("sire (name)",        lambda h: book[h].get("sire"), lambda h: recs[h].get("sire_name"), lambda h: recs[h].get("sire_id")),
        ("dam (name)",         lambda h: book[h].get("dam"), lambda h: recs[h].get("dam_name"), lambda h: recs[h].get("dam_id")),
        ("brand",              lambda h: book[h].get("brand"), lambda h: recs[h].get("brand"), None),
    ]
    conflicts = collections.defaultdict(list)
    aliases = collections.defaultdict(list)
    for label, getb, getn, getpid in fieldmap:
        cnt = collections.Counter()
        for h in common:
            bk = bucket(getb(h), getn(h))
            # a name "CONFLICT" is really an alias if the book name matches a
            # nickname the website lists for the resolved parent.
            if bk == "CONFLICT" and getpid:
                bname = norm(getb(h))
                if bname and any(norm(n) == bname for n in parent_nicks(getpid(h))):
                    bk = "alias"
                    aliases[label].append((h, getb(h), getn(h)))
            if bk:
                cnt[bk] += 1
            if bk == "CONFLICT":
                conflicts[label].append((h, getb(h), getn(h)))
        same, sp, cf = cnt.get("same", 0), cnt.get("spelling", 0), cnt.get("CONFLICT", 0)
        al, bo, no = cnt.get("alias", 0), cnt.get("book-only", 0), cnt.get("new-only", 0)
        print(f"  {label:22} same={same:3}  spelling={sp:3}  alias={al:2}  CONFLICT={cf:2}  app-only={bo:2}  scrape-only={no:2}")

    # --- new (proposed) fields the scrape adds: coverage over ALL scraped horses ---
    print("\n=== NEW FIELDS added by the scrape (coverage over all {} scraped) ===".format(len(recs)))
    newf = ["coat_pattern", "markings", "genotype", "birth_location", "breeder", "owner",
            "auction_number", "sire_id", "dam_id"]
    for f in newf:
        filled = sum(1 for r in recs.values() if r.get(f))
        print(f"  {f:16} {filled:4}/{len(recs)}")
    flags = {k: sum(1 for r in recs.values() if r.get(k)) for k in
             ("misty_descendant", "buyback", "feral", "half_chincoteague")}
    print(f"  lineage flags    {flags}")

    # --- terminology: prose term vs roster term (build the normalization map) ---
    print("\n=== TERMINOLOGY: prose coat_pattern vs roster color term ===")
    term = collections.Counter()
    for h in common:
        p = recs[h].get("coat_pattern")
        rc = (roster.get(h, {}).get("color") or "")
        if p:
            in_roster = p in rc
            mapped = PATTERN_NORM.get(p, p)
            term[(p, mapped, mapped in rc or in_roster)] += 1
    for (p, mapped, ok), n in term.most_common():
        verdict = "roster agrees" if ok else "ABSENT from roster term"
        print(f"  prose '{p}' -> norm '{mapped}'  x{n}  ({verdict})")

    # --- aliases auto-resolved via nicknames (book call-name -> website formal name) ---
    print("\n=== ALIASES auto-resolved (book name is a nickname the site lists; NOT a conflict) ===")
    for label, items in aliases.items():
        if items:
            print(f"  {label}:")
            for h, bk, nv in items:
                print(f"    id={h:5}  book={bk!r:24} -> site formal name {nv!r}")

    # --- the genuine conflicts to eyeball ---
    print("\n=== CONFLICTS to review (website is canonical, but worth a human glance) ===")
    any_cf = False
    for label, items in conflicts.items():
        if items:
            any_cf = True
            print(f"  {label}:")
            for h, bk, nv in items[:20]:
                print(f"    id={h:5}  app={bk!r:30} scrape={nv!r}")
    if not any_cf:
        print("  (none -- every flagged diff resolved to spelling, alias, or website-more-precise)")

    if args.field:
        print(f"\n=== every row for '{args.field}' ===")
        for h in common:
            b = book[h]
            r = recs[h]
            print(f"  id={h:5} {b.get('name'):30} app={b.get(args.field)!r:24} "
                  f"roster={roster.get(h,{}).get(args.field)!r:20} "
                  f"prose_color={r.get('color')!r} pattern={r.get('coat_pattern')!r}")


if __name__ == "__main__":
    main()
