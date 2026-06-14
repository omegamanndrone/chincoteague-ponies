"""Merge accepted changeset items into the authoring DB (IMPLEMENTATION_PLAN.md §6).

ADDITIVE & PEDIGREE-KEYED. We never alter the existing local-id-keyed `horses` /
`horse_photos` tables. K's harvested canon data is born keyed by pedigree_id in
NEW tables, so Phase 1's local->pedigree cutover doesn't have to remap it:

  region_observations(pedigree_id, region, observed, source)   -- ephemeral, dated (band-like)
  bands(mare_pedigree_id, stallion_pedigree_id, date_recorded, source)
  field_photos(filename, pedigree_id, credit, source, detection_conf)

All inserts are INSERT OR REPLACE on natural keys => re-merging is idempotent.
Accepted photo crops are copied into out/canon_photos/ (the build step later moves
them into app assets). NOTES ARE NEVER MERGED (local-only, §0.1).

This module is import-used by the console's /merge route and also runnable standalone.
"""

from __future__ import annotations

import json
import shutil
import sqlite3
from pathlib import Path

from remap import DEFAULT_DB

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"

SCHEMA = """
CREATE TABLE IF NOT EXISTS region_observations (
    pedigree_id INTEGER NOT NULL,
    region      TEXT    NOT NULL,
    observed    TEXT    NOT NULL,
    source      TEXT,
    PRIMARY KEY (pedigree_id, observed)
);
CREATE TABLE IF NOT EXISTS bands (
    mare_pedigree_id     INTEGER NOT NULL,
    stallion_pedigree_id INTEGER NOT NULL,
    date_recorded        TEXT    NOT NULL,
    source               TEXT,
    PRIMARY KEY (mare_pedigree_id, stallion_pedigree_id, date_recorded)
);
CREATE TABLE IF NOT EXISTS field_photos (
    filename       TEXT PRIMARY KEY,
    pedigree_id    INTEGER NOT NULL,
    credit         TEXT,
    source         TEXT,
    detection_conf REAL
);
"""


# Phase 2 scrape canon tables. Pedigree-keyed, like the ingest tables above, so
# they sit ALONGSIDE the untouched local-id `horses` book table; build_assets
# overlays them by pedigree_id (don't-clobber). A re-scrape simply replaces these.
SCRAPE_SCHEMA = """
CREATE TABLE IF NOT EXISTS scraped_horses (
    pedigree_id      INTEGER PRIMARY KEY,
    name             TEXT, nickname TEXT, state TEXT,
    color            TEXT, coat_pattern TEXT, sex TEXT,
    markings         TEXT,            -- JSON array
    genotype         TEXT, eye_color TEXT, brand TEXT,
    birth_year       TEXT, birth_date TEXT, birth_location TEXT,
    breeder          TEXT, owner TEXT,
    auction_price    TEXT, auction_number TEXT, buyback_donor TEXT,
    registry         TEXT, registry_number TEXT,
    sire_id          INTEGER, sire_name TEXT, dam_id INTEGER, dam_name TEXT,
    misty_descendant INTEGER, buyback INTEGER, feral INTEGER, half_chincoteague INTEGER,
    background       TEXT, qr_video_url TEXT, dsc_photo_url TEXT
);
CREATE TABLE IF NOT EXISTS departed_horses (
    pedigree_id INTEGER PRIMARY KEY,
    name        TEXT
);
"""

# columns of scraped_horses in insert order (drives the parametrized INSERT)
SCRAPE_COLS = [
    "pedigree_id", "name", "nickname", "state", "color", "coat_pattern", "sex",
    "markings", "genotype", "eye_color", "brand", "birth_year", "birth_date",
    "birth_location", "breeder", "owner", "auction_price", "auction_number",
    "buyback_donor", "registry", "registry_number", "sire_id", "sire_name",
    "dam_id", "dam_name", "misty_descendant", "buyback", "feral",
    "half_chincoteague", "background", "qr_video_url", "dsc_photo_url",
]
_BOOL_COLS = {"misty_descendant", "buyback", "feral", "half_chincoteague"}


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)


def merge_scrape(out_dir: Path, db_path: Path, decisions: dict) -> dict:
    """Merge the website re-scrape changeset into the authoring DB (additive,
    pedigree-keyed). Writes `scraped_horses` (the current roster + enrichment) and
    `departed_horses` (the delete list), applying the reviewer's decisions:
      - rejected new_horse  -> that pony is NOT written (don't add it)
      - accepted departed   -> recorded for deletion at build
      - rejected field_change -> that scrape column is NULLED so build's don't-clobber
                                 keeps the book value
    """
    changeset = json.loads((out_dir / "changeset.json").read_text(encoding="utf-8"))
    actions = effective_actions(changeset, decisions)
    items = {it["id"]: it for it in changeset["items"]}
    records = {int(k): dict(v) for k, v in changeset["scrape_records"].items()}

    rejected_new = {items[i]["pedigree_id"] for i, a in actions.items()
                    if items[i]["type"] == "new_horse" and a != "accept"}
    departed_accept = [(items[i]["pedigree_id"], items[i]["name"]) for i, a in actions.items()
                       if items[i]["type"] == "departed" and a == "accept"]
    # rejected field_change -> null that scrape column so the book value survives
    field_overrides = 0
    for i, a in actions.items():
        it = items[i]
        if it["type"] == "field_change" and a != "accept":
            records.get(it["pedigree_id"], {})[it["scrape_col"]] = None
            field_overrides += 1

    report = {"scraped_horses": 0, "new_added": 0, "new_skipped": len(rejected_new),
              "departed": 0, "field_overrides": field_overrides}
    book_ids = _book_pedigree_ids(db_path)

    con = sqlite3.connect(db_path)
    try:
        con.executescript(SCRAPE_SCHEMA)
        con.execute("DELETE FROM scraped_horses")   # re-scrape fully replaces this table
        con.execute("DELETE FROM departed_horses")
        placeholders = ",".join("?" for _ in SCRAPE_COLS)
        for pid, rec in records.items():
            if pid in rejected_new:
                continue
            rec["markings"] = json.dumps(rec.get("markings") or [], ensure_ascii=False)
            for b in _BOOL_COLS:
                rec[b] = 1 if rec.get(b) else 0
            con.execute(
                f"INSERT OR REPLACE INTO scraped_horses ({','.join(SCRAPE_COLS)}) VALUES ({placeholders})",
                [rec.get(c) for c in SCRAPE_COLS])
            report["scraped_horses"] += 1
            if pid not in book_ids:
                report["new_added"] += 1
        for pid, name in departed_accept:
            con.execute("INSERT OR REPLACE INTO departed_horses (pedigree_id, name) VALUES (?,?)",
                        (pid, name))
            report["departed"] += 1
        con.commit()
    finally:
        con.close()
    return report


def _book_pedigree_ids(db_path: Path) -> set[int]:
    import re
    con = sqlite3.connect(db_path)
    ids = set()
    for (url,) in con.execute("SELECT qr_pedigree_url FROM horses"):
        m = re.search(r"id=(\d+)", url or "")
        if m:
            ids.add(int(m.group(1)))
    con.close()
    return ids


def effective_actions(changeset: dict, decisions: dict) -> dict[str, str]:
    """Per-item final action: reviewer decision overrides the item's default."""
    return {it["id"]: decisions.get(it["id"], it["default_action"]) for it in changeset["items"]}


def merge(out_dir: Path = DEFAULT_OUT, db_path: Path = DEFAULT_DB,
          decisions: dict | None = None) -> dict:
    decisions = decisions or {}
    changeset = json.loads((out_dir / "changeset.json").read_text(encoding="utf-8"))
    if changeset.get("source") == "scrape":   # Phase 2 website re-scrape
        return merge_scrape(out_dir, db_path, decisions)
    actions = effective_actions(changeset, decisions)
    items = {it["id"]: it for it in changeset["items"]}

    canon_dir = out_dir / "canon_photos"
    canon_dir.mkdir(parents=True, exist_ok=True)

    report = {"photo": 0, "region": 0, "band": 0, "skipped": 0, "rejected": 0,
              "photo_missing_crop": 0, "notes_local": 0}

    con = sqlite3.connect(db_path)
    try:
        ensure_schema(con)
        for item_id, action in actions.items():
            it = items[item_id]
            t = it["type"]
            if t == "note":
                report["notes_local"] += 1
                continue
            if action != "accept":
                report["rejected" if action == "reject" else "skipped"] += 1
                continue

            if t == "photo":
                src = out_dir / (it.get("cropped_path") or "")
                if not it.get("cropped_path") or not src.exists():
                    report["photo_missing_crop"] += 1
                    continue
                fname = Path(it["cropped_path"]).name
                shutil.copy2(src, canon_dir / fname)
                con.execute(
                    "INSERT OR REPLACE INTO field_photos"
                    "(filename, pedigree_id, credit, source, detection_conf) VALUES (?,?,?,?,?)",
                    (fname, it["pedigree_id"], it["credit"], it["source"], it.get("detection_conf")))
                report["photo"] += 1
            elif t == "region":
                con.execute(
                    "INSERT OR REPLACE INTO region_observations"
                    "(pedigree_id, region, observed, source) VALUES (?,?,?,?)",
                    (it["pedigree_id"], it["region"], it["observed"], "kristina_backup"))
                report["region"] += 1
            elif t == "band":
                con.execute(
                    "INSERT OR REPLACE INTO bands"
                    "(mare_pedigree_id, stallion_pedigree_id, date_recorded, source) VALUES (?,?,?,?)",
                    (it["mare_pedigree_id"], it["stallion_pedigree_id"],
                     it["date_recorded"], "kristina_backup"))
                report["band"] += 1
        con.commit()
    finally:
        con.close()
    report["canon_photos_dir"] = str(canon_dir)
    return report


if __name__ == "__main__":
    import argparse
    import sys
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Merge accepted changeset items (uses defaults if no review_state.json).")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()
    state = args.out / "review_state.json"
    decisions = json.loads(state.read_text(encoding="utf-8")) if state.exists() else {}
    rep = merge(args.out, args.db, decisions)
    print("merge complete:", rep)
