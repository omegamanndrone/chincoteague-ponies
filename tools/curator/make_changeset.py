"""Build a reviewable changeset from the normalized ingest + crop manifest.

Step 3 of the curator pipeline (IMPLEMENTATION_PLAN.md §6). Turns the produced
data (out/normalized.json + out/crop_manifest.json) into a flat list of typed,
reviewable items that the Flask console renders for Accept/Reject, and that the
merge step writes into the authoring DB.

Item types:
  photo   — a YOLO crop (original <-> cropped); accept => primary field photo (K. Kent)
  region  — a dated N/S observation (ephemeral, band-like); accept => region_observations
  band    — a dated mare->stallion sighting; accept => bands. Stale (not current) default REJECT
  note    — a personal note. LOCAL-ONLY, NEVER CANON (§0.1) => default SKIP, shown for the
            departed-gate / cutover remap only.

Default actions encode our policy so a reviewer mostly confirms:
  photo: accept (or 'review' if no horse detected) · region: accept ·
  band: accept if current else reject · note: skip.

Output: out/changeset.json. The console layers per-item decisions on top via
out/review_state.json, so re-running this never loses your review choices.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

from normalize import bucket, canonical_color, norm, normalize_coat_pattern, sexn
from remap import DEFAULT_DB

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"
SCRAPE_OUT = HERE / "out" / "scrape"


def build(out_dir: Path) -> dict:
    normalized = json.loads((out_dir / "normalized.json").read_text(encoding="utf-8"))
    crop_path = out_dir / "crop_manifest.json"
    crops = json.loads(crop_path.read_text(encoding="utf-8")) if crop_path.exists() else {"photos": []}
    crop_by_file = {c["filename"]: c for c in crops.get("photos", [])}

    items: list[dict] = []

    # --- photos (prefer crop manifest; it has the cropped path + detection) ---
    for p in normalized.get("photos", []):
        c = crop_by_file.get(p["original_filename"], {})
        detected = c.get("horse_detected", False)
        items.append({
            "id": f"photo:{p['original_filename']}",
            "type": "photo",
            "pedigree_id": p["pedigree_id"], "name": p["name"],
            "original_path": p["original_path"],
            "cropped_path": c.get("cropped_path"),
            "horse_detected": detected,
            "detection_conf": c.get("detection_conf"),
            "crop_box": c.get("crop_box"),
            "source": p["source"], "credit": p["credit"],
            "default_action": "accept" if detected else "review",
        })

    # --- regions (ephemeral dated observations) ---
    for r in normalized.get("regions", []):
        items.append({
            "id": f"region:{r['pedigree_id']}",
            "type": "region",
            "pedigree_id": r["pedigree_id"], "name": r["name"],
            "region": r["region"], "observed": r["region_observed"],
            "default_action": "accept",
        })

    # --- bands (current accepted; stale defaults to reject) ---
    for b in normalized.get("bands", []):
        items.append({
            "id": f"band:{b['remapped_key']}",
            "type": "band",
            "mare_pedigree_id": b["mare_pedigree_id"], "mare_name": b["mare_name"],
            "stallion_pedigree_id": b["stallion_pedigree_id"], "stallion_name": b["stallion_name"],
            "date_recorded": b["date_recorded"], "is_current": b["is_current"],
            # Keep ALL dated sightings as history (the app shows current + truncates
            # the card to 2 years). Reject is reserved for genuinely incorrect entries.
            "default_action": "accept",
        })

    # --- notes (LOCAL ONLY — never canon; surfaced for the departed-gate) ---
    for n in normalized.get("notes_local", []):
        items.append({
            "id": f"note:{n['pedigree_id']}",
            "type": "note",
            "pedigree_id": n["pedigree_id"], "name": n["name"], "note": n["note"],
            "canon": False,
            "default_action": "skip",
        })

    type_counts: dict[str, int] = {}
    for it in items:
        type_counts[it["type"]] = type_counts.get(it["type"], 0) + 1

    return {
        "source_file": normalized.get("source_file"),
        "observed_date": normalized.get("observed_date"),
        "counts": type_counts,
        "total": len(items),
        "warnings": normalized.get("warnings", []),
        "items": items,
    }


# ----------------------------------------------------------------------------
# Scrape source (Phase 2). Diff parsed.json + rosters.json vs the authoring DB
# into typed items the SAME console reviews:
#   new_horse    — a current-roster pony with no book row (11 VA + 88 MD). accept => add.
#   departed     — a book horse no longer on either Current roster (×6). accept => delete.
#                  default 'review' if it carries canon data (photos/bands/regions), else 'accept'.
#   field_change — a genuine book-vs-scrape value conflict (color/dam/brand …). The website is
#                  canonical (more precise/correct), so default 'accept'; surfaced for spot-check.
#                  REJECT => merge nulls that scrape field so the book value survives (don't-clobber).
#
# The full normalized record for EVERY current pony is embedded as `scrape_records`
# (pedigree-keyed) so the merge step writes `scraped_horses` straight from the changeset
# — same contract as ingest (changeset.json + review_state.json -> DB). The merge applies
# the review decisions: rejected new_horse omitted, rejected field_change field nulled,
# accepted departed recorded for deletion.
# ----------------------------------------------------------------------------

# Fields compared book-vs-scrape to surface genuine conflicts. (Most resolve to
# same/spelling/alias and are NOT surfaced; only CONFLICT becomes a field_change.)
_COMPARE = [
    ("color", lambda bk, rec, ros: bk.get("color"), lambda bk, rec, ros: ros.get("color")),
    ("sex", lambda bk, rec, ros: sexn(bk.get("sex")), lambda bk, rec, ros: sexn(rec.get("sex"))),
    ("birth_year", lambda bk, rec, ros: bk.get("birth_year"), lambda bk, rec, ros: rec.get("birth_year")),
    ("eye_color", lambda bk, rec, ros: bk.get("eye_color"), lambda bk, rec, ros: rec.get("eye_color")),
    ("auction_price", lambda bk, rec, ros: re.sub(r"[^\d]", "", bk.get("auction_price") or ""),
     lambda bk, rec, ros: rec.get("auction_price")),
    ("buyback_donor", lambda bk, rec, ros: bk.get("buyback_donor"), lambda bk, rec, ros: rec.get("buyback_donor")),
    ("brand", lambda bk, rec, ros: bk.get("brand"), lambda bk, rec, ros: rec.get("brand")),
    ("sire", lambda bk, rec, ros: bk.get("sire"), lambda bk, rec, ros: rec.get("sire_name")),
    ("dam", lambda bk, rec, ros: bk.get("dam"), lambda bk, rec, ros: rec.get("dam_name")),
]
# field_change -> which scrape column the merge should null on REJECT (keep book).
_FIELD_TO_SCRAPE_COL = {
    "color": "color", "eye_color": "eye_color", "auction_price": "auction_price",
    "buyback_donor": "buyback_donor", "brand": "brand", "sire": "sire_name", "dam": "dam_name",
}


def _normalized_record(pid: int, rec: dict, ros: dict, state: str) -> dict:
    """One pedigree-keyed scraped_horses row: parse fields + roster color/nickname,
    normalization map applied. This is exactly what the merge writes."""
    nicks = ros.get("nicknames") or []
    return {
        "pedigree_id": pid,
        "name": rec.get("name") or ros.get("name"),
        "nickname": nicks[0] if nicks else None,
        "state": state,
        "color": canonical_color(ros.get("color"), rec.get("color")),  # roster wins
        "coat_pattern": normalize_coat_pattern(rec.get("coat_pattern")),
        "sex": rec.get("sex"),
        "markings": rec.get("markings") or [],
        "genotype": rec.get("genotype"),
        "eye_color": rec.get("eye_color"),
        "brand": rec.get("brand"),
        "birth_year": rec.get("birth_year"),
        "birth_date": rec.get("birth_date"),
        "birth_location": rec.get("birth_location"),
        "breeder": rec.get("breeder"),
        "owner": rec.get("owner"),
        "auction_price": rec.get("auction_price"),
        "auction_number": rec.get("auction_number"),
        "buyback_donor": rec.get("buyback_donor"),
        "registry": rec.get("registry"),
        "registry_number": rec.get("registry_number"),
        "sire_id": rec.get("sire_id"),
        "sire_name": rec.get("sire_name"),
        "dam_id": rec.get("dam_id"),
        "dam_name": rec.get("dam_name"),
        "misty_descendant": bool(rec.get("misty_descendant")),
        "buyback": bool(rec.get("buyback")),
        "feral": bool(rec.get("feral")),
        "half_chincoteague": bool(rec.get("half_chincoteague")),
        "background": rec.get("background"),
        "qr_video_url": rec.get("qr_video_url"),
        "dsc_photo_url": rec.get("dsc_photo_url"),
    }


def build_scrape(scrape_dir: Path, db_path: Path) -> dict:
    parsed = {int(k): v for k, v in
              json.loads((scrape_dir / "parsed.json").read_text(encoding="utf-8")).items()}
    ros_all = json.loads((scrape_dir / "rosters.json").read_text(encoding="utf-8"))["rosters"]
    cur_va = {r["id"]: r for r in ros_all["roster_virginia_current"]}
    cur_md = {r["id"]: r for r in ros_all["roster_maryland_current"]}
    roster = {}  # current first; used for color/nickname/alias-nicknames
    for src in (cur_va, cur_md, {r["id"]: r for r in ros_all["roster_virginia_past"]},
                {r["id"]: r for r in ros_all["roster_maryland_past"]}):
        for pid, r in src.items():
            roster.setdefault(pid, r)
    scrape_ids = set(cur_va) | set(cur_md)

    # book rows keyed by pedigree_id (from qr_pedigree_url)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    book: dict[int, dict] = {}
    for row in con.execute("SELECT * FROM horses"):
        m = re.search(r"id=(\d+)", row["qr_pedigree_url"] or "")
        if m:
            book[int(m.group(1))] = dict(row)

    def has_canon(pid: int) -> dict:
        return {
            "photos": con.execute("SELECT COUNT(*) FROM field_photos WHERE pedigree_id=?", (pid,)).fetchone()[0],
            "regions": con.execute("SELECT COUNT(*) FROM region_observations WHERE pedigree_id=?", (pid,)).fetchone()[0],
            "bands": con.execute("SELECT COUNT(*) FROM bands WHERE mare_pedigree_id=? OR stallion_pedigree_id=?",
                                 (pid, pid)).fetchone()[0],
        }

    book_ids = set(book)
    overlap = sorted(book_ids & scrape_ids)
    new_ids = sorted(scrape_ids - book_ids)
    departed_ids = sorted(book_ids - scrape_ids)

    # nicknames of a resolved parent (so a book call-name vs site formal name is an
    # alias, not a conflict) — mirrors reconcile.py.
    def parent_nicks(parent_pid):
        return [norm(n) for n in (roster.get(parent_pid, {}).get("nicknames") or [])] if parent_pid else []

    items: list[dict] = []
    scrape_records: dict[str, dict] = {}

    # full normalized record for every current pony (what merge writes)
    for pid in sorted(scrape_ids):
        state = "VA" if pid in cur_va else "MD"
        scrape_records[str(pid)] = _normalized_record(pid, parsed.get(pid, {}), roster.get(pid, {}), state)

    # --- field_change: genuine conflicts among the overlap (website canonical) ---
    for pid in overlap:
        bk, rec, ros = book[pid], parsed.get(pid, {}), roster.get(pid, {})
        for field, getb, getn in _COMPARE:
            b_val, n_val = getb(bk, rec, ros), getn(bk, rec, ros)
            verdict = bucket(b_val, n_val)
            if verdict == "CONFLICT" and field in ("sire", "dam"):
                parent_pid = rec.get(f"{field}_id")
                if norm(b_val) and norm(b_val) in parent_nicks(parent_pid):
                    verdict = "alias"  # book call-name == site nickname -> not a conflict
            if verdict == "CONFLICT":
                items.append({
                    "id": f"field_change:{pid}:{field}",
                    "type": "field_change",
                    "pedigree_id": pid, "name": bk.get("name"),
                    "field": field, "book_value": b_val, "scrape_value": n_val,
                    "scrape_col": _FIELD_TO_SCRAPE_COL.get(field, field),
                    "default_action": "accept",  # website wins; reject => keep book
                })

    # --- new_horse: in a Current roster, no book row (11 VA + 88 MD) ---
    for pid in new_ids:
        rec, ros = parsed.get(pid, {}), roster.get(pid, {})
        state = "VA" if pid in cur_va else "MD"
        items.append({
            "id": f"new_horse:{pid}", "type": "new_horse",
            "pedigree_id": pid, "name": rec.get("name") or ros.get("name"),
            "state": state, "color": canonical_color(ros.get("color"), rec.get("color")),
            "sex": rec.get("sex"), "age": ros.get("age"),
            "markings": rec.get("markings") or [],
            "default_action": "accept",
        })

    # --- departed: book horse off both Current rosters (×6); canon-data gated ---
    for pid in departed_ids:
        canon = has_canon(pid)
        clean = sum(canon.values()) == 0
        items.append({
            "id": f"departed:{pid}", "type": "departed",
            "pedigree_id": pid, "name": book[pid].get("name"),
            "canon": canon, "clean": clean,
            # safe auto-delete when nothing of K's is attached; else hold for a human
            "default_action": "accept" if clean else "review",
        })

    con.close()

    type_counts: dict[str, int] = {}
    for it in items:
        type_counts[it["type"]] = type_counts.get(it["type"], 0) + 1

    return {
        "source": "scrape",
        "counts": type_counts,
        "total": len(items),
        "roster_summary": {"overlap": len(overlap), "new": len(new_ids),
                           "new_va": len(set(new_ids) & set(cur_va)),
                           "new_md": len(set(new_ids) & set(cur_md)),
                           "departed": len(departed_ids), "current_total": len(scrape_ids)},
        "scrape_records": scrape_records,
        "warnings": [],
        "items": items,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", choices=["ingest", "scrape"], default="ingest",
                    help="ingest = K's backup (default); scrape = website re-scrape (Phase 2)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--scrape-dir", type=Path, default=SCRAPE_OUT)
    ap.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = ap.parse_args()

    if args.source == "scrape":
        if not (args.scrape_dir / "parsed.json").exists():
            sys.exit(f"no parsed.json in {args.scrape_dir} -- run scrape_pedigrees.py + parse_pedigree.py first")
        cs = build_scrape(args.scrape_dir, args.db)
        (args.out / "changeset.json").write_text(json.dumps(cs, indent=2, ensure_ascii=False), encoding="utf-8")
        rs = cs["roster_summary"]
        print(f"scrape changeset: {cs['total']} review items {cs['counts']}")
        print(f"  roster: {rs['current_total']} current ({rs['overlap']} overlap + {rs['new']} new"
              f" [{rs['new_va']} VA, {rs['new_md']} MD]); {rs['departed']} departed")
        print(f"  scrape_records embedded: {len(cs['scrape_records'])}")
        print(f"  -> {args.out / 'changeset.json'}")
        return

    if not (args.out / "normalized.json").exists():
        sys.exit(f"no normalized.json in {args.out} -- run ingest_backup.py first")
    cs = build(args.out)
    (args.out / "changeset.json").write_text(json.dumps(cs, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"changeset: {cs['total']} items {cs['counts']}")
    if not (args.out / "crop_manifest.json").exists():
        print("  note: no crop_manifest.json yet -- photos lack crops (run crop_photos.py)")
    print(f"  -> {args.out / 'changeset.json'}")


if __name__ == "__main__":
    main()
