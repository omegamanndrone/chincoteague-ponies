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
| YOLO crop + watermark (§3c) | _todo_ | reads `out/normalized.json` → `photos[].original_path` |
| Changeset diff (§6) | `make_changeset.py` _todo_ | diffs normalized data vs `horses.db` |
| Flask review console (§6) | _todo_ | click-through Accept/Reject |
| Build assets (§6) | `build_assets.py` _todo_ | DB → `assets/horses_data.json` + photos |

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

**Notes are local-only and never canon** (§0.1). They appear in `normalized.json`
only so the cutover remap+re-import (§4) can find them — do not merge them into canon.

## Why ID remap is by-lookup, never in place

10+ app local ids (1–143) collide with a *different* horse's `pedigree_id`. `remap.py`
translates via the authoring DB; nothing renumbers in place. Phase 1 then promotes
`pedigree_id` to the canonical `id` everywhere.
