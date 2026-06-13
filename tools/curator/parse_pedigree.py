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


_STOP = r"(?:Registry|Born |Brand:|Auction|" + "|".join(COLORS) + r"|$)"


def _registry(fam):
    """'Registry Number: NPS number: N9BFT-KP' -> ('NPS', 'N9BFT-KP'). Org formats:
    NPS (park), CVFC (fire company), ICPAR (the registry); plus bare codes/typos."""
    m = re.search(r"Registry Number:\s*([A-Za-z0-9#:,\.\- ]+?)\s*" + _STOP, fam)
    if not m:
        return None, None
    raw = m.group(1).strip().rstrip(",").strip()
    if re.search(r"NPS", raw, re.I):
        org = "NPS"
    elif re.search(r"ICPAR", raw, re.I):
        org = "ICPAR"
    elif re.search(r"C.?F.?C", raw, re.I):  # CVFC / CFVC typo
        org = "CVFC"
    else:
        org = None
    num = None
    for pat in (r"#\s*([A-Za-z0-9\-]+)",            # ICPAR #BB5
                r"numb\w*:?\s*([A-Za-z0-9\-]+)",    # 'number:'/'Number:'/'numbrer:' code
                r"([A-Za-z0-9][A-Za-z0-9\-]{3,})\s*$"):  # bare trailing code
        mm = re.search(pat, raw, re.I)
        if mm:
            num = mm.group(1)
            break
    return org, num


# a description sentence is "structured" (a field we already extract) if it leads
# with a known label, is the color/sex/markings sentence, the eye sentence, or a
# bare genotype. Everything else is free narrative -> the canon `background` blurb.
_STRUCT_PREFIX = re.compile(
    r"^(?:Breeder|Owner|Auction price|Auction number|Auction Video|Buyback donor|"
    r"Brand|Registry Number|Registry|Born|First seen)\b|^Buyback donors?\b", re.I)
_COLOR_RE = re.compile(r"\b(?:" + "|".join(COLORS) + r")\b", re.I)
_SEX_RE = re.compile(r"\b(?:" + "|".join(SEXES) + r")\b", re.I)
_GENO_ONLY = re.compile(r"(?:[A-Za-z]{1,3}/[A-Za-z]{1,3}\s*,?\s*)+$")


def _is_structured(s):
    s = s.strip().rstrip(".").strip()
    if not s or s.startswith("["):
        return True
    if _STRUCT_PREFIX.match(s):
        return True
    if _COLOR_RE.search(s) and _SEX_RE.search(s):   # color/sex/markings sentence
        return True
    if re.search(r"\beyes$", s, re.I):              # 'Brown eyes'
        return True
    if _GENO_ONLY.fullmatch(s):                     # 'TO/TO, A/a, E/e'
        return True
    return False


def _background(fam_html):
    """The residual narrative prose (donation stories, Alternate sire/dam, Misty
    descent, nicknames-of-note) after the structured fields are removed. Supersedes
    the old book_info (which was a subset of this same prose)."""
    # anchor text = the media link labels (DSC/video/etc.); not narrative -> drop
    desc = re.sub(r"<a\b[^>]*>.*?</a>", " ", fam_html, flags=re.S | re.I)
    desc = re.sub(r"<[^>]+>", " ", desc).replace("&nbsp;", " ").replace("&amp;", "&")
    desc = re.sub(r"\s+", " ", desc).strip()
    desc = re.sub(r"^\s*\[[^\]]*\]\s*", "", desc)   # leading nickname bracket
    desc = re.sub(r"\s+\.", ".", desc)              # '$6,700 .' -> '$6,700.'
    narrative = [s.strip() for s in re.split(r"(?<=\.)\s+", desc) if not _is_structured(s)]
    bg = " ".join(narrative).strip()
    return bg or None


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
    rec["breeder"] = (re.search(r"Breeder:\s*(.*?)\s*(?:Owner:|" + _STOP[3:], fam) or [None, None])[1]
    rec["owner"] = (re.search(r"Owner:\s*(.*?)\s*" + _STOP, fam) or [None, None])[1]
    if rec["breeder"]:
        rec["breeder"] = rec["breeder"].strip() or None
    if rec["owner"]:
        rec["owner"] = rec["owner"].strip() or None
    rec["registry"], rec["registry_number"] = _registry(fam)

    rec.update(_desc_fields(fam))

    rec["eye_color"] = (re.search(r"([A-Za-z]+)\s+eyes\.", fam) or [None, None])[1]
    rec["auction_price"] = (re.search(r"Auction price:\s*\$?\s*([\d,]+)", fam) or [None, None])[1]
    rec["auction_number"] = (re.search(r"Auction number:\s*(\S+?)\.", fam) or [None, None])[1]
    # detailed birth date: 'June 25, 2011' or 'May 2004'
    rec["birth_date"] = (re.search(r"Born\s+([A-Z][a-z]+(?:\s+\d{1,2})?,?\s+\d{4})(?!\s+in\b)", fam)
                         or [None, None])[1]
    rec["buyback_donor"] = (re.search(r"Buyback donors?:\s*([^.]+?)\.", fam) or [None, None])[1]
    rec["brand"] = (re.search(r"Brand:\s*([^.]+?)\.", fam) or [None, None])[1]
    # genotype tokens e.g. E/e, TO/n, A/A, CR/n
    geno = re.findall(r"\b([A-Za-z]{1,3}/[A-Za-z]{1,3})\b", fam)
    rec["genotype"] = ", ".join(geno) if geno else None

    # media link-outs
    rec["qr_video_url"] = (re.search(r'href="([^"]+)"[^>]*>\s*Identifying Chincoteague Ponies Video', fam_html)
                           or [None, None])[1]
    rec["dsc_photo_url"] = (re.search(r'href="([^"]+)"[^>]*>\s*Photos at DSC Photography', fam_html)
                            or [None, None])[1]

    rec["background"] = _background(fam_html)  # canon narrative; supersedes book_info

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
