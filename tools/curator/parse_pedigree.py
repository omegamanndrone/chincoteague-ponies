#!/usr/bin/env python
"""parse_pedigree.py -- grammar parser for cached pedigree.php pages.

Phase 2, step 2 (IMPLEMENTATION_PLAN.md S5/S6). Consumes the raw HTML cached by
scrape_pedigrees.py and turns each pony page into the structured fields the refresh
adds: enrichment columns, sire_id/dam_id, and the M/B/F/H lineage flags.

Per page it extracts:
  identity     name, nicknames(*from roster), main-horse M/B/F/H flags
  physical     color (base), coat_pattern, sex, markings[], eye_color, genotype
  birth        birth_year, birth_date, birth_location
  provenance   breeder, owner, auction_price, auction_number, buyback_donor, brand
  lineage      sire_id, dam_id  (the gen-1 chart cells, by id)
  media        qr_video_url (Identifying Chincoteague Ponies clip), dsc_photo_url

The M/B/F/H flags come from the indicators <sup> on the MAIN name in the chart,
NOT the prose (S5). The full-sibling marker is intentionally NOT scraped -- it is
derived from parent matches by the app-side family resolver.

  python parse_pedigree.py                 # parse all cached pages -> out/scrape/parsed.json + coverage
  python parse_pedigree.py --id 3          # dump one parsed page as JSON
  python parse_pedigree.py --validate      # cross-check vs the 143 horses in horses.db
"""
import argparse
import json
import os
import re
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out", "scrape")
RAW = os.path.join(OUT, "raw")
DB = os.path.normpath(os.path.join(HERE, "..", "..", "horses.db"))

# vocab (S5 / pedigree-site-scraping memory)
PATTERNS = ["tobiano", "overo", "sabino", "splash", "roan pinto", "pinto", "solid"]
# normalize prose terminology -> common usage (matches the roster/app `color`). The
# prose always says "tobiano" where the roster says "pinto" (decided 2026-06-12).
PATTERN_NORM = {"tobiano": "pinto"}
SEXES = ["female", "male", "stallion", "mare", "gelding", "colt", "filly"]
COLORS = ["Bay", "Chestnut", "Black", "Palomino", "Buckskin", "Grey", "Gray", "Dun",
          "Brown", "Roan", "White", "Cremello", "Perlino", "Smoky", "Golden", "Silver"]
# anchored on the color->sex grammar so it locks onto the right sentence regardless
# of what the breeder/owner free-text contains: "Bay tobiano female with blaze, ..."
DESC_RE = re.compile(
    r"\b(?P<color>(?:" + "|".join(COLORS) + r")[A-Za-z ]*?)\s+"
    r"(?P<sex>" + "|".join(SEXES) + r")\b"
    r"(?:\s+with\s+(?P<marks>[^.]*?))?\.",
    re.I,
)


def _strip(html):
    """tags -> spaces, collapse whitespace; keeps text content."""
    txt = re.sub(r"<[^>]+>", " ", html)
    txt = txt.replace("&nbsp;", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", txt).strip()


def _main_cell(html):
    """The mainfemale/mainmale chart cell: name, sex-from-class, M/B/F/H flags."""
    m = re.search(r"class='main(female|male)'>(.*?)<br", html, re.S)
    if not m:
        return None
    sex_cls = "female" if m.group(1) == "female" else "male"
    inner = m.group(2)
    sup = re.search(r"class=indicators>\s*<sup>(.*?)</sup>", inner, re.S)
    flags = set(re.findall(r"[MBFH]", sup.group(1))) if sup else set()
    # drop the indicators span so its flag letters don't leak into the name
    name_html = re.sub(r"<span class=indicators>.*?</span>", "", inner, flags=re.S)
    name = re.sub(r"<[^>]+>", "", name_html).strip()
    name = re.sub(r"\s+", " ", name)
    return name, sex_cls, flags


def _family_div(html):
    """The description block text inside the main cell's class=family div."""
    m = re.search(r"class=family>(.*?)</div>\s*</td>", html, re.S)
    return m.group(1) if m else ""


def _sire_dam(html):
    """Gen-1 sire/dam = the first rowspan='4' male / female chart cells (id + name)."""
    sire = dam = None
    sire_name = dam_name = None
    for cls, hid, name in re.findall(
            r"rowspan='4'[^>]*class='(male|female)'>\s*<a href=pedigree\.php\?id=(\d+)[^>]*>([^<]+)</a>",
            html):
        if cls == "male" and sire is None:
            sire, sire_name = int(hid), name.strip()
        elif cls == "female" and dam is None:
            dam, dam_name = int(hid), name.strip()
    return sire, sire_name, dam, dam_name


def _desc_fields(fam):
    """'Bay tobiano female with blaze, four stockings.' -> color/pattern/sex/markings."""
    out = {"color": None, "coat_pattern": None, "sex": None, "markings": []}
    m = DESC_RE.search(fam)
    if not m:
        return out
    out["sex"] = m.group("sex").lower()
    if m.group("marks"):
        marks = re.split(r",|\band\b", m.group("marks"))
        out["markings"] = [s.strip() for s in marks if s.strip()]
    color_phrase = m.group("color").strip()
    # pull a coat pattern out of the color phrase; remainder is the base color
    low = color_phrase.lower()
    for p in PATTERNS:
        if re.search(r"\b" + re.escape(p) + r"\b", low):
            out["coat_pattern"] = PATTERN_NORM.get(p, p)  # tobiano -> pinto (common usage)
            color_phrase = re.sub(r"\b" + re.escape(p) + r"\b", "", color_phrase, flags=re.I)
            break
    color_phrase = re.sub(r"\s+", " ", color_phrase).strip()
    out["color"] = color_phrase or None
    return out


def parse_pedigree(html, hid):
    rec = {"id": hid}
    mc = _main_cell(html)
    if mc:
        name, sex_cls, flags = mc
        rec["name"] = name
        rec["misty_descendant"] = "M" in flags
        rec["buyback"] = "B" in flags
        rec["feral"] = "F" in flags
        rec["half_chincoteague"] = "H" in flags
    else:
        rec["name"] = None
        for k in ("misty_descendant", "buyback", "feral", "half_chincoteague"):
            rec[k] = False

    fam_html = _family_div(html)
    fam = _strip(fam_html)

    # structured lines (separated by <br> in source)
    rec["birth_location"] = None
    rec["birth_year"] = None
    m = re.search(r"Born\s+(\d{4})\s+in\s+([^.]+?)\.", fam)
    if m:
        rec["birth_year"] = m.group(1)
        rec["birth_location"] = m.group(2).strip()
    rec["breeder"] = (re.search(r"Breeder:\s*([^<]*?)\s*(?:Owner:|Born |Brand:|$)", fam) or [None, None])[1]
    rec["owner"] = (re.search(r"Owner:\s*([^<]*?)\s*(?:Born |Brand:|Bay|Chestnut|Black|$)", fam) or [None, None])[1]
    if rec["breeder"]:
        rec["breeder"] = rec["breeder"].strip() or None
    if rec["owner"]:
        rec["owner"] = rec["owner"].strip() or None

    rec.update(_desc_fields(fam))

    rec["eye_color"] = (re.search(r"([A-Za-z]+)\s+eyes\.", fam) or [None, None])[1]
    rec["auction_price"] = (re.search(r"Auction price:\s*\$?\s*([\d,]+)", fam) or [None, None])[1]
    rec["auction_number"] = (re.search(r"Auction number:\s*(\S+?)\.", fam) or [None, None])[1]
    # detailed birth date: 'June 25, 2011' or 'May 2004'
    rec["birth_date"] = (re.search(r"Born\s+([A-Z][a-z]+(?:\s+\d{1,2})?,?\s+\d{4})(?!\s+in\b)", fam)
                         or [None, None])[1]
    rec["buyback_donor"] = (re.search(r"Buyback donor:\s*([^.]+?)\.", fam) or [None, None])[1]
    rec["brand"] = (re.search(r"Brand:\s*([^.]+?)\.", fam) or [None, None])[1]
    # genotype tokens e.g. E/e, TO/n, A/A, CR/n
    geno = re.findall(r"\b([A-Za-z]{1,3}/[A-Za-z]{1,3})\b", fam)
    rec["genotype"] = ", ".join(geno) if geno else None

    # media link-outs
    rec["qr_video_url"] = (re.search(r'href="([^"]+)"[^>]*>\s*Identifying Chincoteague Ponies Video', fam_html)
                           or [None, None])[1]
    rec["dsc_photo_url"] = (re.search(r'href="([^"]+)"[^>]*>\s*Photos at DSC Photography', fam_html)
                            or [None, None])[1]

    rec["sire_id"], rec["sire_name"], rec["dam_id"], rec["dam_name"] = _sire_dam(html)
    # tidy strings
    for k, v in rec.items():
        if isinstance(v, str):
            rec[k] = v.strip() or None
    return rec


def _load(hid):
    p = os.path.join(RAW, f"pedigree_{hid}.html")
    if not os.path.exists(p):
        return None
    return open(p, encoding="utf-8").read()


def cached_ids():
    ids = []
    for f in os.listdir(RAW):
        m = re.match(r"pedigree_(\d+)\.html$", f)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


def parse_all():
    recs = {}
    for hid in cached_ids():
        recs[hid] = parse_pedigree(_load(hid), hid)
    return recs


def coverage(recs):
    n = len(recs)
    fields = ["name", "color", "coat_pattern", "sex", "markings", "eye_color",
              "auction_price", "auction_number", "birth_year", "birth_date",
              "birth_location", "breeder", "owner", "buyback_donor", "brand",
              "genotype", "sire_id", "dam_id"]
    print(f"\nCoverage over {n} cached pages:")
    for f in fields:
        filled = sum(1 for r in recs.values() if r.get(f))
        print(f"  {f:16} {filled:4d}/{n}  ({100*filled//n if n else 0}%)")
    flagged = {k: sum(1 for r in recs.values() if r.get(k))
               for k in ("misty_descendant", "buyback", "feral", "half_chincoteague")}
    print("  flags:", flagged)


def validate(recs):
    """Cross-check parsed sire/dam ids + sex against the 143 known horses in horses.db."""
    if not os.path.exists(DB):
        print("no horses.db to validate against")
        return
    c = sqlite3.connect(DB)
    book = {}
    for row in c.execute("SELECT qr_pedigree_url, name, sex, sire, dam, color FROM horses"):
        m = re.search(r"id=(\d+)", row[0] or "")
        if m:
            book[int(m.group(1))] = dict(name=row[1], sex=row[2], sire=row[3], dam=row[4], color=row[5])
    common = [hid for hid in book if hid in recs]
    print(f"\nValidate: {len(common)} of {len(book)} book horses have a parsed page.")
    sex_ok = sire_ok = sire_chk = dam_ok = dam_chk = 0
    mismatches = []

    def norm(s):
        s = (s or "").lower().strip()
        # book spells numbers out; site uses digits ("Fifteen" <-> "15")
        words = {"fifteen": "15", "twelve": "12", "eleven": "11", "ten": "10"}
        for w, d in words.items():
            s = re.sub(r"\b" + w + r"\b", d, s)
        return re.sub(r"[^a-z0-9 ]", "", s)

    for hid in common:
        b, r = book[hid], recs[hid]
        bsex = "female" if (b["sex"] or "").lower() in ("mare", "female", "filly") else \
               "male" if (b["sex"] or "").lower() in ("stallion", "male", "gelding", "colt") else None
        if bsex and r.get("sex"):
            rsex = "female" if r["sex"] in ("female", "mare", "filly") else "male"
            sex_ok += (bsex == rsex)
        # sire/dam name cross-check against the chart's own inline parent name
        if r.get("sire_name") and b["sire"]:
            sire_chk += 1
            if norm(r["sire_name"]) == norm(b["sire"]) or norm(r["sire_name"]) in norm(b["sire"]) \
               or norm(b["sire"]) in norm(r["sire_name"]):
                sire_ok += 1
            else:
                mismatches.append((hid, "sire", b["sire"], r["sire_name"]))
        if r.get("dam_name") and b["dam"]:
            dam_chk += 1
            if norm(r["dam_name"]) == norm(b["dam"]) or norm(r["dam_name"]) in norm(b["dam"]) \
               or norm(b["dam"]) in norm(r["dam_name"]):
                dam_ok += 1
            else:
                mismatches.append((hid, "dam", b["dam"], r["dam_name"]))
    print(f"  sex match:  {sex_ok}/{len(common)}")
    print(f"  sire match: {sire_ok}/{sire_chk} (name vs book)")
    print(f"  dam  match: {dam_ok}/{dam_chk} (name vs book)")
    if mismatches:
        print(f"  {len(mismatches)} name mismatches (book spelling vs site) -- sample:")
        for hid, kind, bk, pn in mismatches[:15]:
            print(f"    id={hid:5} {kind}: book={bk!r} site={pn!r}")


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--id", type=int, help="dump one parsed page")
    ap.add_argument("--validate", action="store_true", help="cross-check vs horses.db")
    args = ap.parse_args()

    if args.id:
        html = _load(args.id)
        if not html:
            print(f"no cached page for id={args.id}; run scrape_pedigrees.py first")
            sys.exit(1)
        print(json.dumps(parse_pedigree(html, args.id), indent=2, ensure_ascii=False))
        return

    ids = cached_ids()
    if not ids:
        print("no cached pedigree pages; run scrape_pedigrees.py first")
        sys.exit(1)
    recs = parse_all()
    out = os.path.join(OUT, "parsed.json")
    json.dump(recs, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"Parsed {len(recs)} pages -> {out}")
    coverage(recs)
    if args.validate:
        validate(recs)


if __name__ == "__main__":
    main()
