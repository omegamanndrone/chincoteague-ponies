# Chincoteague/Assateague Ponies App — Data Refresh, ID Conversion & Photo Pipeline

_Updated 2026-06-10. Source site: `chincoteaguepedigrees.com` (static HTML, ISO-8859-1)._

## 0. Product context (shapes every decision)

Right now the app is a **field collection tool** for Kristina: access the public pedigree data fast/streamlined, and add her own observations, band relationships, and photos. After she has built a library of **unique, uncopyrighted** photos and fleshed out band relationships, we add features (history blurbs, etc.) and **sell it publicly with annual updates** that track the website plus our unique content. So: build everything public-facing, but the immediate job is data/photo collection.

Implication: **almost everything in Kristina's backup becomes canon** (ships to all future users) — the exception is any genuinely personal free-text notes, which I'll surface for review before shipping.

## 1. Sequencing (per your direction)

1. **Phase 0 — capture & integrate Kristina's device data** (do this first).
2. **Phase 1 — convert the whole system to the website's identifier (`pedigree_id`).**
3. Then enrichment, MD herd, markings search, family tree (Phases 2+).

## 2. Source data inventory (verified)

| Herd view (`herds.php`, POST) | Count | Role |
|---|---|---|
| Virginia / Current | 148 | Primary VA roster (app has 143 today; **11 missing**, 6 app horses departed) |
| Virginia / Past | 411 | Deceased/removed — **not imported** (see §8) |
| Maryland / Current | 88 | **New** MD (NPS) roster |
| Maryland / Past | 328 | **Not imported** |

Per-pony page `pedigree.php?id=N`: description block + 4-gen pedigree (sire/dam linked by id) + progeny + siblings. Static HTML; needs browser-like headers or returns HTTP 406. Description grammar is consistent across VA + MD → one parser. Marking vocabulary (pattern/face/legs/body/genotype) lives in the prose and is parseable. (Details in memory: `pedigree-site-scraping`.)

## 3. Phase 0 — Capture & integrate Kristina's device data

### 3a. Capture (smoothest path — no cable)
The app's built-in **Backup** (list screen → backup icon → Backup) calls `exportUserData()` and writes `chincoteague_backup_DATE.json` — a self-contained file with notes, herds, bands, photo metadata, **and every device photo base64-encoded**. Save to Files/iCloud → bring to project dir. (No iOS sandbox extraction needed.)

### 3b. Inspect & triage canon
On receipt, I report exact counts (photos / bands / herds / notes) and dump the notes text. Policy: **everything → canon except flagged-personal notes.** Photos and band/herd observations are the whole point of collection.

### 3c. YOLO auto-crop pipeline (offline, on this machine)
Reuse the DRONE BRAIN YOLO stack (`ultralytics 8.4.17`, `cv2`, PIL — all verified present). For each device photo:
1. Run detection; filter to class `horse`.
2. Pick the **largest-area** horse box.
3. Expand the box by a small buffer (default ~6% of box w/h) **clamped to image bounds** so the horse never touches the crop edge.
4. Write the cropped image as the canon display photo.

- **Model:** default stock `yolov8m.pt` (COCO `horse`, best for ground-level tourist photos); farm_guardian weights (`models/farm_guardian_*/weights/best.pt`, also has `horse`=17) as fallback.
- **No horse detected:** keep original uncropped, flag for manual review.
- **Originals archived** (never discarded) so we can re-crop with different params later. Cropped version is what ships.

### 3d. Offline ID remap (single device → no in-app migration code)
Because it's one device, we remap her backup **offline** rather than shipping migration logic:
- Translate every horse-id key from local id → `pedigree_id` using the complete, verified mapping (all 143 horses carry their pedigree_id in `qr_pedigree_url`).
- **Bands need both ids remapped** — keys are `${horseId}_${stallionId}_${date}` and values store both; translate key + values.
- Photo-blob keys are filenames → unchanged.
- Output: a pedigree-id-keyed backup she restores once after installing the new build.

⚠️ Must be done by export→transform→rebuild, **not in place**: 10+ of the old local ids (e.g. local 42 = "A Splash of Freckles") collide with a *different* horse's pedigree id, so in-place renumbering is ambiguous.

## 4. Phase 1 — Convert to `pedigree_id` as the canonical identifier

- `pedigree_id` **becomes the `id`** everywhere: `horses_data.json`, Hive keys, sire/dam relationships. The old arbitrary local id (1–143) is retired.
- Relationships are then trivial: `sire_id`/`dam_id` *are* pedigree ids; the family tree resolves with no indirection.
- Reserve an id range (e.g. `≥ 900000`) for any future **app-local** horse Kristina adds that the website hasn't catalogued yet, so it can't collide with a real pedigree_id. (This phase she annotates existing catalogued horses; brand-new foals arrive via the next scrape.)

## 5. Schema changes (`horses`)

Existing columns stay. `id` is repurposed to hold pedigree_id. New columns (all nullable, additive):
`state` (VA/MD), `life_status` (current/past), `coat_pattern`, `markings`, `genotype`, `birth_location`, `breeder`, `owner`, `auction_number`, `registry`, `registry_number`, `sire_id`, `dam_id`, `dsc_photo_url` (copyrighted gallery link-out).

New `horse_markings` table (`horse_id`, `marking`) for marking-based search. Progeny/siblings are **derived by query** (`WHERE sire_id=? OR dam_id=?`) — no extra tables, no card clutter.

## 6. Build pipeline (reproducible — including the currently-missing DB→JSON step)

1. `scrape_pedigrees.py` — fetch VA+MD Current rosters; for each id fetch `pedigree.php`, **cache raw HTML**, throttle ~1.5 s.
2. `parse_pedigree.py` — grammar parser → structured fields + marking tokens + sire/dam ids.
3. `build_db.py` — write `horses.db`, regenerate `assets/horses_data.json` keyed by pedigree_id.
   - **MERGE semantics (critical for annual updates):** canon photos/bands/herds collected from Kristina are keyed by pedigree_id and must be **preserved/merged** on every re-scrape — the scrape refreshes public fields only, never clobbers our unique content.
4. Validation: every current-herd pony present; spot-check 5 end-to-end; confirm Kristina's remapped data round-trips.

## 7. App changes (Flutter)

- `horse.dart` — new fields in model/`fromMap`/`toMap`/`copyWith`.
- `data_service.dart` — load new fields; `state` (VA/MD) filter; marking search; family resolver by id; **user-photo-primary** ordering (flip `getFirstPhotoForHorse` to prefer `source != 'book'`).
- `horse_list_screen.dart` — VA/MD toggle; marking filter chips; graceful empty-photo tiles; optional "past/departed" filter (default hidden).
- `horse_detail_screen.dart` — show markings/pattern/genotype/registry; single tappable **Family** row → tree; keep video/pedigree links; photo gallery with K's photos first.
- New family tree screen (current-herd nodes clickable; others plain names).

## 8. Photos, family tree & licensing

- **Book photos (280):** kept, `source='book'`, demoted to secondary. Never deleted.
- **Kristina's photos:** YOLO-cropped, `source='user'`, **primary** image — this is the "slowly replace book photos" path.
- **Family tree:** **do not import dead/removed horses.** Ancestors not in current VA/MD herds show as plain non-clickable names; tree dead-ends there. (The 6 already-in-app departed horses are *kept* — they may hold K's data/book photos — marked `life_status='past'` and hidden from the default list.)
- **DSC Photography galleries** & **identifyingchincoteagueponies.com videos:** copyrighted → **link out only, never download/rehost.**
- **Pedigree text:** factual/public, maintainers invite contributions → scrape politely.

## 9. Phasing

0. Capture K's backup → inspect/triage → YOLO-crop → offline ID-remap. _(needs the backup file)_
1. Convert system to pedigree_id; rebuild DB/JSON; K restores remapped backup.
2. Add 11 missing VA ponies + `life_status`; surface enrichment fields on detail screen.
3. Markings search.
4. MD herd + VA/MD toggle.
5. Family tree navigation.
6. Polish (DSC link-out, device-photo replacement UX, history-blurb groundwork for sale).

## 10. Remaining open questions (defaulted — tell me to change any)

- **Crop buffer %** — default 6% of box dims, clamped to image. _(easy to tune after we see results on real photos)_
- **Crop model** — default stock `yolov8m.pt`; switch to farm_guardian if it crops better on her shots. _(decide empirically on a sample)_
- **Departed-6 horses** — default: keep, mark `past`, hide from default list. Alternative: delete.
- **App-local id range** for future uncatalogued horses — default reserve `≥ 900000`.
- **Pending input:** Kristina's backup file itself — canon-vs-personal on *notes* is the only triage that waits on seeing real content.

_No remaining blockers to start Phase 0 the moment the backup file lands._
