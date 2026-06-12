"""Ingest Kristina's device backup -> normalized, pedigree-id-keyed intermediate.

This is step 1 of the curator ingest pipeline (IMPLEMENTATION_PLAN.md §3d, the
"offline ID remap"). It reads the raw device backup, validates it against the
authoring DB, remaps every local id to its pedigree_id, extracts the full-res
photo originals to disk (archived, never discarded), and emits a single
normalized.json that the downstream steps consume:

    YOLO crop+watermark  -> reads photos[].original_path
    make_changeset.py    -> reads regions / bands / photos
    (notes_local stay LOCAL -- never canon, surfaced here only for the cutover
     remap+re-import described in §4)

It does NOT touch horses.db and produces NO canon changes -- it only normalizes.
Review + merge happen later in the Flask console.

Backup format (from BackupService.exportUserData, v1):
  user_data        {local_id: {"herd"?: "northern|southern", "notes"?: str}}
  bands            {"<mare>_<stallion>_<date>": {horse_id, stallion_id, date_recorded}}
  user_photo_meta  {local_id: JSON-STRING of [{id,horse_id,filename,source}]}  (double-encoded!)
  user_photo_blobs {filename: base64 JPEG/MPO}

Usage:
    python ingest_backup.py [BACKUP.json] [--out OUTDIR] [--db horses.db]
Defaults: newest chincoteague_backup_*.json under Kristina_data/, out/ alongside this file.
"""

from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from collections import defaultdict
from pathlib import Path

from remap import REPO_ROOT, DEFAULT_DB, Remapper

try:
    from PIL import Image
except ImportError:  # Pillow is expected (used by the crop step too), but degrade gracefully.
    Image = None

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"
BACKUP_DIR = REPO_ROOT / "Kristina_data"

# Provenance for harvested photos -- NOT generic 'user' (see §3c.1 / §5).
PHOTO_SOURCE = "field"
PHOTO_CREDIT = "K. Kent"


def find_latest_backup() -> Path:
    candidates = sorted(BACKUP_DIR.glob("chincoteague_backup_*.json"))
    if not candidates:
        raise FileNotFoundError(f"no chincoteague_backup_*.json in {BACKUP_DIR}")
    return candidates[-1]


def decode_photo_meta(raw) -> list[dict]:
    """user_photo_meta values are JSON strings (Hive stored them encoded)."""
    if isinstance(raw, str):
        return json.loads(raw)
    return raw or []


def ingest(backup_path: Path, out_dir: Path, db_path: Path) -> dict:
    rm = Remapper.from_db(db_path)
    backup = json.loads(backup_path.read_text(encoding="utf-8"))

    observed_date = (backup.get("exported_at") or "")[:10] or None
    warnings: list[str] = []

    def require(local_id: int, ctx: str) -> bool:
        if not rm.has_local(local_id):
            warnings.append(f"{ctx}: local id {local_id} not found in authoring DB -- dropped")
            return False
        return True

    # --- regions + local notes (both live in user_data) --------------------
    regions: list[dict] = []
    notes_local: list[dict] = []
    region_ids: set[int] = set()
    for key, val in backup.get("user_data", {}).items():
        local_id = int(key)
        if not require(local_id, "user_data"):
            continue
        h = rm.horse(local_id)
        herd = (val or {}).get("herd")
        if herd:
            region_ids.add(local_id)
            regions.append({
                "pedigree_id": h.pedigree_id, "local_id": local_id, "name": h.name,
                "region": herd, "region_observed": observed_date,
            })
        note = ((val or {}).get("notes") or "").strip()
        if note:
            notes_local.append({
                "pedigree_id": h.pedigree_id, "local_id": local_id, "name": h.name,
                "note": note,
            })

    # --- bands (remap BOTH ids; mark current vs stale per mare) -------------
    raw_bands = backup.get("bands", {})
    # mare_local -> [(date, stallion_local, status)]. status defaults to "present";
    # "left" markers (written by the app's band-remove fix) are departures, not
    # memberships -- they decide "current" but never enter canon.
    by_mare: dict[int, list[tuple[str, int, str]]] = defaultdict(list)
    valid_band_keys: list[str] = []
    for key, val in raw_bands.items():
        mare, stallion = val["horse_id"], val["stallion_id"]
        if not (require(mare, "band mare") and require(stallion, "band stallion")):
            continue
        valid_band_keys.append(key)
        by_mare[mare].append((val["date_recorded"], stallion, val.get("status", "present")))

    # Latest-dated entry per mare decides her current band; if it's a departure
    # ("left"), she currently has no band.
    latest_by_mare = {mare: max(sightings) for mare, sightings in by_mare.items()}
    bands: list[dict] = []
    for key in valid_band_keys:
        val = raw_bands[key]
        if val.get("status", "present") == "left":
            continue  # departure marker -- not a canon membership
        mare, stallion, date = val["horse_id"], val["stallion_id"], val["date_recorded"]
        mh, sh = rm.horse(mare), rm.horse(stallion)
        _ld, ls, lstatus = latest_by_mare[mare]
        # Current unless superseded by a DIFFERENT stallion later (repeated same-
        # stallion sightings are all valid history), or the mare has since departed.
        is_current = lstatus != "left" and stallion == ls
        bands.append({
            "remapped_key": f"{mh.pedigree_id}_{sh.pedigree_id}_{date}",
            "mare_pedigree_id": mh.pedigree_id, "stallion_pedigree_id": sh.pedigree_id,
            "mare_local_id": mare, "stallion_local_id": stallion,
            "mare_name": mh.name, "stallion_name": sh.name,
            "date_recorded": date, "is_current": is_current,
        })
    for mare, sightings in by_mare.items():
        if len({s for _, s, st in sightings if st != "left"}) > 1:
            mh = rm.horse(mare)
            warnings.append(
                f"band: mare {mh.name} (ped {mh.pedigree_id}) banded with multiple "
                f"stallions across dates -- only latest kept as current (prune stale in console)"
            )

    # --- photos (extract originals to disk; archive, never discard) ---------
    photos_dir = out_dir / "photos_original"
    photos_dir.mkdir(parents=True, exist_ok=True)
    blobs = backup.get("user_photo_blobs", {})
    photos: list[dict] = []
    photo_ids: set[int] = set()
    referenced_files: set[str] = set()
    for key, raw_meta in backup.get("user_photo_meta", {}).items():
        local_id = int(key)
        if not require(local_id, "photo"):
            continue
        h = rm.horse(local_id)
        for m in decode_photo_meta(raw_meta):
            fname = m["filename"]
            referenced_files.add(fname)
            b64 = blobs.get(fname)
            if b64 is None:
                warnings.append(f"photo: meta {fname} (id {local_id}) has no blob -- skipped")
                continue
            data = base64.b64decode(b64)
            dest = photos_dir / fname
            dest.write_bytes(data)
            width = height = None
            fmt = None
            if Image is not None:
                try:
                    with Image.open(io.BytesIO(data)) as im:
                        width, height, fmt = im.width, im.height, im.format
                except Exception as e:  # noqa: BLE001
                    warnings.append(f"photo: {fname} could not be decoded as image ({e})")
            photo_ids.add(local_id)
            photos.append({
                "pedigree_id": h.pedigree_id, "local_id": local_id, "name": h.name,
                "original_filename": fname,
                "original_path": dest.relative_to(out_dir).as_posix(),
                "width": width, "height": height, "format": fmt,
                "source": PHOTO_SOURCE, "credit": PHOTO_CREDIT,
            })
    orphan_blobs = sorted(set(blobs) - referenced_files)
    for fname in orphan_blobs:
        warnings.append(f"photo: blob {fname} has no meta entry -- not extracted")

    # --- data-quality cross-checks (feed the console / departed gate) ------
    for local_id in sorted((photo_ids | set(by_mare)) - region_ids):
        h = rm.horse(local_id)
        warnings.append(
            f"region gap: {h.name} (ped {h.pedigree_id}) has photos/bands but no N/S region assignment"
        )
    DEPARTURE_HINTS = ("died", "passed", "moved", "roadside", "lost vision")
    for n in notes_local:
        if any(w in n["note"].lower() for w in DEPARTURE_HINTS):
            warnings.append(
                f"departed-gate: note on {n['name']} (ped {n['pedigree_id']}) mentions "
                f"death/move -- confirm against live roster before deletion (§8)"
            )

    return {
        "source_file": backup_path.name,
        "backup_version": backup.get("version"),
        "exported_at": backup.get("exported_at"),
        "observed_date": observed_date,
        "photo_source": PHOTO_SOURCE,
        "photo_credit": PHOTO_CREDIT,
        "counts": {
            "regions": len(regions), "bands": len(bands),
            "bands_current": sum(b["is_current"] for b in bands),
            "photos": len(photos), "photo_horses": len(photo_ids),
            "notes_local": len(notes_local), "warnings": len(warnings),
        },
        "regions": sorted(regions, key=lambda r: r["pedigree_id"]),
        "bands": sorted(bands, key=lambda b: (b["mare_pedigree_id"], b["date_recorded"])),
        "photos": sorted(photos, key=lambda p: p["pedigree_id"]),
        "notes_local": sorted(notes_local, key=lambda n: n["pedigree_id"]),
        "warnings": warnings,
    }


def main() -> None:
    # The plan text uses § etc.; keep console output legible on Windows (cp1252).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("backup", nargs="?", type=Path, help="backup json (default: newest in Kristina_data/)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output dir (default: tools/curator/out)")
    ap.add_argument("--db", type=Path, default=DEFAULT_DB, help="authoring DB (default: horses.db)")
    args = ap.parse_args()

    backup_path = args.backup or find_latest_backup()
    args.out.mkdir(parents=True, exist_ok=True)

    result = ingest(backup_path, args.out, args.db)
    out_file = args.out / "normalized.json"
    out_file.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")

    c = result["counts"]
    print(f"ingested {backup_path.name} (v{result['backup_version']}, observed {result['observed_date']})")
    print(f"  regions {c['regions']} | bands {c['bands']} ({c['bands_current']} current) | "
          f"photos {c['photos']} across {c['photo_horses']} horses | notes {c['notes_local']} (local)")
    print(f"  -> {out_file.relative_to(REPO_ROOT)}")
    print(f"  -> {(args.out / 'photos_original').relative_to(REPO_ROOT)}/ ({c['photos']} originals)")
    if c["warnings"]:
        print(f"  {c['warnings']} warning(s):")
        for w in result["warnings"]:
            print(f"    - {w}")


if __name__ == "__main__":
    main()
