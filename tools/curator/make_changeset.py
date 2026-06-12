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
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"


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
            "default_action": "accept" if b["is_current"] else "reject",
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


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

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
