"""build_assets.py — authoring DB -> app assets (IMPLEMENTATION_PLAN.md §6, step 4).

The currently-missing DB->JSON build step. Reads the authoring `horses.db` and
emits the app's bundled `horses_data.json` in the **decided pedigree-keyed,
separate-sections shape** (§6), plus copies field-photo crops into the assets
photo dir.

This is BOTH the one-time cutover build and the recurring re-scrape build — same
shape every time. It re-keys horses from the arbitrary local id to `pedigree_id`
(by lookup via qr_pedigree_url, never in place) and assembles four top-level
sections:

  horses[]  id=pedigree_id; sire_id/dam_id (null until the scrape resolves them);
            §5 enrichment fields emitted when their columns exist, else null.
  photos[]  book (horse_photos, local-keyed -> remapped) + field (field_photos,
            already pedigree-keyed) with `credit`; field sorted ahead of book.
  bands[]   {mare_id, stallion_id, date_recorded} from the `bands` table.
  regions[] {id, region, observed} from `region_observations` (dated/ephemeral).

The canon tables (field_photos/bands/region_observations) are created by the
Curator merge; if they don't exist yet (pre-merge), those sections come out empty
— so this runs safely as a DRY RUN today and proves the re-keying on real data.

SAFE BY DEFAULT: writes to tools/curator/out/build/ (gitignored). Point --out at
horse_app/assets to actually deploy.

Usage (from the curator venv or plain python — stdlib only):
    python build_assets.py                      # dry run -> out/build/
    python build_assets.py --out ../../horse_app/assets   # real deploy target
"""

from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import sys
from pathlib import Path

from remap import REPO_ROOT, DEFAULT_DB, Remapper

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out" / "build"
CANON_PHOTOS = HERE / "out" / "canon_photos"          # field crops, written by merge
BOOK_PHOTOS = REPO_ROOT / "horse_app" / "assets" / "photos"

# §5 enrichment fields — emitted as null until the columns exist (scrape adds them).
ENRICH_FIELDS = [
    "state", "coat_pattern", "markings", "genotype", "birth_location",
    "breeder", "owner", "auction_number", "registry", "registry_number",
    "dsc_photo_url",
]
# §5 pedigree-chart flag codes (M/B/F/H). Emitted as null until the scrape
# resolves them, so the JSON shape is FINAL now and the app never needs a second
# device migration to gain these columns. (★ full-sibling is derived, not stored.)
LINEAGE_FLAGS = ["misty_descendant", "buyback", "feral", "half_chincoteague"]
# Columns we deliberately drop from the shipped record (build-time only / superseded).
DROP_COLS = {"id", "herd", "pdf_page_data", "pdf_page_photo"}


def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    return con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def build(db_path: Path, out_dir: Path) -> dict:
    rm = Remapper.from_db(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    out_dir.mkdir(parents=True, exist_ok=True)

    horse_cols = {r[1] for r in con.execute("PRAGMA table_info(horses)")}

    # --- horses[] : re-keyed to pedigree_id ------------------------------
    # id_map (local id -> pedigree_id) is emitted as a SEPARATE, non-personal
    # asset (id_remap.json) the app uses once at cutover to remap the user's
    # local-only notes onto the new keys — see data_service._restoreRemappedNotes.
    horses = []
    id_map: dict[str, int] = {}
    for row in con.execute("SELECT * FROM horses"):
        ped = rm.to_pedigree(row["id"])
        id_map[str(row["id"])] = ped
        rec: dict = {"id": ped}
        for col in horse_cols:
            if col not in DROP_COLS:
                rec[col] = row[col]
        rec["sire_id"] = None  # resolved by the scrape (pedigree links); names kept in sire/dam
        rec["dam_id"] = None
        for f in ENRICH_FIELDS:
            rec.setdefault(f, row[f] if f in horse_cols else None)
        for f in LINEAGE_FLAGS:
            rec.setdefault(f, bool(row[f]) if f in horse_cols else None)
        horses.append(rec)
    horses.sort(key=lambda h: h["id"])

    # --- photos[] : book (remapped) + field (pedigree-keyed) -------------
    photos = []
    for r in con.execute("SELECT horse_id, filename, source FROM horse_photos"):
        photos.append({"horse_id": rm.to_pedigree(r["horse_id"]),
                       "filename": r["filename"], "source": r["source"], "credit": None})
    if _table_exists(con, "field_photos"):
        for r in con.execute("SELECT pedigree_id, filename, credit, source FROM field_photos"):
            photos.append({"horse_id": r["pedigree_id"], "filename": r["filename"],
                           "source": r["source"], "credit": r["credit"]})
    # field before book, then by horse
    photos.sort(key=lambda p: (p["horse_id"], 0 if p["source"] != "book" else 1))

    # --- bands[] / regions[] : from merged canon tables ------------------
    bands = []
    if _table_exists(con, "bands"):
        for r in con.execute(
                "SELECT mare_pedigree_id, stallion_pedigree_id, date_recorded FROM bands"):
            bands.append({"mare_id": r["mare_pedigree_id"],
                          "stallion_id": r["stallion_pedigree_id"],
                          "date_recorded": r["date_recorded"]})
    # region_observations preserves dated history (a horse accrues a row per
    # backup/scrape date); the app ships only the CURRENT snapshot, so emit the
    # latest observation per horse.
    regions = []
    if _table_exists(con, "region_observations"):
        for r in con.execute(
                "SELECT pedigree_id, region, observed FROM region_observations r "
                "WHERE observed = (SELECT MAX(observed) FROM region_observations "
                "WHERE pedigree_id = r.pedigree_id)"):
            regions.append({"id": r["pedigree_id"], "region": r["region"], "observed": r["observed"]})
    con.close()

    data = {
        "schema": "pedigree-id-v1",
        "horses": horses, "photos": photos, "bands": bands, "regions": regions,
    }
    (out_dir / "horses_data.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    # Public-safe id map (numbers only — no personal data). Bundled so the app
    # can remap the user's local notes old->pedigree on the one-time cutover.
    (out_dir / "id_remap.json").write_text(
        json.dumps(id_map, indent=2), encoding="utf-8")

    # --- copy field-photo crops into the target photos dir ---------------
    photos_out = out_dir / "photos"
    copied = 0
    if CANON_PHOTOS.exists():
        photos_out.mkdir(parents=True, exist_ok=True)
        for f in CANON_PHOTOS.glob("*"):
            shutil.copy2(f, photos_out / f.name)
            copied += 1

    n_field = sum(1 for p in photos if p["source"] != "book")
    return {
        "horses": len(horses), "photos": len(photos), "photos_field": n_field,
        "photos_book": len(photos) - n_field, "bands": len(bands), "regions": len(regions),
        "field_crops_copied": copied, "id_remap": len(id_map),
        "out_json": out_dir / "horses_data.json",
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="output dir (default: tools/curator/out/build — a safe dry run)")
    args = ap.parse_args()
    if not args.db.exists():
        sys.exit(f"authoring DB not found: {args.db}")

    rep = build(args.db, args.out)
    deploying = args.out.resolve() != DEFAULT_OUT.resolve()
    print(f"build_assets {'(DEPLOY)' if deploying else '(dry run)'} -> {args.out}")
    print(f"  horses {rep['horses']} | photos {rep['photos']} "
          f"(book {rep['photos_book']}, field {rep['photos_field']}) | "
          f"bands {rep['bands']} | regions {rep['regions']}")
    print(f"  field crops copied: {rep['field_crops_copied']} "
          f"(book photo files not copied — assumed already in {BOOK_PHOTOS})")
    print(f"  id_remap.json: {rep['id_remap']} local->pedigree entries (non-personal)")
    if rep["bands"] == 0 and rep["regions"] == 0 and rep["photos_field"] == 0:
        print("  note: canon tables empty/absent — run a Curator merge first to populate "
              "bands/regions/field photos (this run proves the horse re-keying).")
    print(f"  -> {rep['out_json']}")


if __name__ == "__main__":
    main()
