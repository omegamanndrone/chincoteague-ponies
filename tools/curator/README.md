# Curator (`tools/curator/`)

Build-time tooling for the ponies app. **This never ships in the app.** It is the
middle layer between the *authoring DB* (`horses.db`, source of truth, local-only)
and the *app* (which consumes only built assets). See `IMPLEMENTATION_PLAN.md` §6.

```
SOURCE ─▶ CHANGESET ─▶ review (Accept/Reject) ─▶ MERGE ─▶ BUILD app assets
  ├─ ingest K's backup.json → {photos+YOLO crops, bands, regions, notes}
  └─ re-scrape website       → {new horses, departed, changed fields}
```

## Status

| Step | Script | State |
|---|---|---|
| Ingest + ID remap (§3d) | `ingest_backup.py` | ✅ built |
| ID mapping helper | `remap.py` | ✅ built |
| YOLO crop + watermark (§3c) | `crop_photos.py` | ✅ built |
| Changeset (§6) | `make_changeset.py` | ✅ built |
| Merge → authoring DB (§6) | `merge.py` | ✅ built |
| Flask review console (§6) | `console.py` | ✅ built |
| Build assets (§6) | `build_assets.py` | ✅ built — scrape overlay (don't-clobber), `background`, drops `book_info`, resolves sire/dam, +99/−6, sex/color/price normalize |
| Scrape rosters + pages (§6, Phase 2) | `scrape_pedigrees.py` | ✅ built — caches 4 rosters + 236 Current pages |
| Parse pedigree pages (§5/§6) | `parse_pedigree.py` | ✅ built — all §5 fields + `background`; `--validate`, `--id N` |
| Reconcile vs app (validation) | `reconcile.py` | ✅ built — app-vs-scrape diff, nickname-alias aware |
| Normalization map (§5) | `normalize.py` | ✅ built — shared tobiano→pinto / roster-color / sex / bucket |
| Scrape → changeset (Phase 2) | `make_changeset.py --source scrape` | ✅ built — 121 items (16 field_change, 99 new_horse, 6 departed) + 236 records |
| Scrape merge (Phase 2) | `merge.py` (`merge_scrape`) | ✅ built — writes `scraped_horses` + `departed_horses`, honors review decisions |

## Environment

The crop step uses its **own** isolated venv — it never touches the Drone_brain
project (we only borrow its ultralytics horse-crop *pattern*, read-only):

```bash
py -3.11 -m venv .venv          # torch/ultralytics have no 3.14 wheels yet
.venv/Scripts/python -m pip install ultralytics opencv-python numpy pillow
# stock yolov8m.pt copied into models/ (gitignored)
```

`ingest_backup.py` / `remap.py` need no special env (stdlib + the system Pillow).
The crop step must run via `.venv/Scripts/python`.

## Ingest

```bash
python ingest_backup.py            # newest Kristina_data/chincoteague_backup_*.json
python ingest_backup.py path/to/backup.json --out out --db ../../horses.db
```

Produces `out/` (gitignored — contains personal data):
- `normalized.json` — pedigree-id-keyed regions / bands / photos / `notes_local`, plus
  `warnings` (region gaps, stale bands to prune, departed-gate hints).
- `photos_original/` — the full-res 12 MP originals, extracted and **archived** (the
  crop step writes the shipped versions; originals are never discarded).

## Crop + watermark

```bash
.venv/Scripts/python crop_photos.py            # reads out/normalized.json
.venv/Scripts/python crop_photos.py --conf 0.25 --buffer 0.06
```

Produces (all in `out/`, gitignored):
- `photos_cropped/` — the shipped images: largest horse cropped with a 6% buffer,
  `© K. Kent` watermark (bottom-right, white + dark outline; size/opacity tunable in
  `crop_photos.py`) + EXIF Artist/Copyright. No-horse-detected photos are passed
  through (watermarked) and flagged `needs_review`.
- `crop_manifest.json` — per-photo detection conf, crop box, review flags.

## Review console

```bash
.venv/Scripts/python make_changeset.py     # build out/changeset.json (typed items)
.venv/Scripts/python console.py            # http://127.0.0.1:5000 (auto-opens)
```

Click through items Accept/Reject per type; photos show **original ↔ crop side-by-side**.
Decisions persist to `out/review_state.json` (layered over each item's default action),
so you can stop and resume. Defaults encode policy: photos `accept` (or `review` if no
horse), regions `accept`, bands `accept` if current else `reject`, notes `skip`.

**Merge** (dashboard button, or `.venv/Scripts/python merge.py`) writes accepted items
into the authoring DB — **additive & pedigree-keyed**, never altering the existing
local-id `horses`/`horse_photos`:
- `field_photos(filename, pedigree_id, credit, source, detection_conf)` + crops copied to `out/canon_photos/`
- `region_observations(pedigree_id, region, observed, source)` — ephemeral, dated (band-like)
- `bands(mare_pedigree_id, stallion_pedigree_id, date_recorded, source)`

Idempotent (INSERT OR REPLACE on natural keys). **Notes are never merged** (local-only).

## Build assets (DB → app JSON)

```bash
python build_assets.py                       # dry run -> out/build/ (safe; does not touch the app)
python build_assets.py --out ../../horse_app/assets   # real deploy target
```

Emits `horses_data.json` in the decided shape — separate top-level pedigree-keyed
sections `horses` / `photos` / `bands` / `regions` (§6) — re-keying horses local→
pedigree by lookup (never in place). Canon sections fill from the merged tables;
absent tables → empty sections, so it runs safely **before** a merge (proves the
re-keying). `sire_id`/`dam_id` and §5 enrichment stay null until the scrape (Phase 2)
provides them. See `IMPLEMENTATION_PLAN.md` §6 breadcrumbs for the path forward.

**Notes are local-only and never canon** (§0.1). They appear in `normalized.json`
only so the cutover remap+re-import (§4) can find them — do not merge them into canon.

## Why ID remap is by-lookup, never in place

10+ app local ids (1–143) collide with a *different* horse's `pedigree_id`. `remap.py`
translates via the authoring DB; nothing renumbers in place. Phase 1 then promotes
`pedigree_id` to the canonical `id` everywhere.
