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


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA)


def effective_actions(changeset: dict, decisions: dict) -> dict[str, str]:
    """Per-item final action: reviewer decision overrides the item's default."""
    return {it["id"]: decisions.get(it["id"], it["default_action"]) for it in changeset["items"]}


def merge(out_dir: Path = DEFAULT_OUT, db_path: Path = DEFAULT_DB,
          decisions: dict | None = None) -> dict:
    decisions = decisions or {}
    changeset = json.loads((out_dir / "changeset.json").read_text(encoding="utf-8"))
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
