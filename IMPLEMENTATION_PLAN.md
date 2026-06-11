# Chincoteague/Assateague Ponies App — Data Refresh, ID Conversion & Photo Pipeline

_Updated 2026-06-10. Source site: `chincoteaguepedigrees.com` (static HTML, ISO-8859-1)._

## 0. Product context (shapes every decision)

Right now the app is a **field collection tool** for Kristina: access the public pedigree data fast/streamlined, and add her own observations, band relationships, and photos. After she has built a library of **unique, uncopyrighted** photos and fleshed out band relationships, we add features (history blurbs, etc.) and **sell it publicly with annual updates** that track the website plus our unique content. So: build everything public-facing, but the immediate job is data/photo collection.

### 0.1. Core architecture principle (canon vs. local)
**The app never auto-uploads anything to canon. Every user's herd edits, notes, and photos live only on their own device. Canon changes _only_ through our build-time curator pipeline.** This is the model a shared/sold app needs — each buyer keeps their own local annotations privately.
- **Normal end user (future):** all their herd edits / notes / photos are local, never propagated.
- **Kristina (super-user / content source):** same local behavior, but we **manually harvest her photos + band/herd observations into canon** via the curator console. **Her notes stay personal/local — never canon** (sloppy working notes we don't want propagated).

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

### 3b. Inspect & harvest to canon
On receipt, I report exact counts (photos / bands / herds / notes). Policy follows the architecture principle (§0.1):
- **Photos + band/herd observations → harvested to canon** (K is the content source; this is the point of collection).
- **Notes → stay personal/local, never canon** — they remain only on K's device.

### 3c. YOLO auto-crop pipeline (offline, on this machine — standalone in `tools/curator/`)
Uses the horse-detection capability only (`ultralytics 8.4.17` + `cv2` + PIL, verified present). **No coupling to the drone_brain project** — we borrow the technique/weights, nothing more. For each device photo:
1. Run detection; filter to class `horse`.
2. Pick the **largest-area** horse box.
3. Expand the box by a small buffer (default ~6% of box w/h) **clamped to image bounds** so the horse never touches the crop edge.
4. Apply attribution (§3c.1).
5. Write the cropped image as the canon display photo.

- **Model:** default stock `yolov8m.pt` (COCO `horse`, best for ground-level tourist photos); farm_guardian weights (`models/farm_guardian_*/weights/best.pt`, also has `horse`=17) as fallback.
- **No horse detected:** keep original uncropped, flag for manual review.
- **Originals archived** (never discarded) so we can re-crop / re-watermark with different params later. Cropped version is what ships.

### 3c.1. Watermark & attribution (built into the crop step — for a sellable product)
Every cropped image is credited to **K. Kent** using the industry-standard two-layer approach (visible mark + embedded metadata):

- **Visible watermark (PIL, available now):** subtle `© K. Kent` baked into a corner (default bottom-right, semi-transparent ~40%, small). Travels with the file if extracted; tunable / can be dialed back.
- **Embedded metadata — IPTC Photo Metadata Standard (the actual industry standard), mirrored to XMP + EXIF:**
  - IPTC `Creator` / By-line + XMP `dc:creator` + EXIF `Artist` = `K. Kent`
  - IPTC `CopyrightNotice` + XMP `dc:rights` + EXIF `Copyright` = `© {year} K. Kent. All rights reserved.`
  - IPTC `Credit` + XMP `photoshop:Credit` = `K. Kent`
  - **Tooling to add:** `exiftool` (industry-standard CLI for IPTC/XMP) — *not yet installed*; `piexif` as a lightweight pure-Python EXIF fallback — *not yet installed*. PIL alone covers the visible mark + minimal EXIF if we want zero new deps initially.
- **Provenance label change:** these are **not** generic `source='user'`. Photos get a `credit` field (`K. Kent`) and a meaningful `source` token (e.g. `field`, replacing `user`) — see §5. Book photos keep their own credit/source.

### 3d. Offline ID remap → bake into canon (build-time, my machine)
This is **Flow 1** (her collected data → canon), distinct from how her device survives the update (**Flow 2**, §4). The remap exists so her exported data can be merged into the authoring DB as canon:
- Translate every horse-id key from local id → `pedigree_id` using the complete, verified mapping (all 143 horses carry their pedigree_id in `qr_pedigree_url`).
- **Bands need both ids remapped** — keys are `${horseId}_${stallionId}_${date}` and values store both; translate key + values.
- Photo-blob keys are filenames → unchanged.
- Output: her photos/bands/herds (and any canon notes) **baked into the new build's assets**, keyed by pedigree_id — not a file she manually restores.

⚠️ Must be done by export→transform→rebuild, **not in place**: 10+ of the old local ids (e.g. local 42 = "A Splash of Freckles") collide with a *different* horse's pedigree id, so in-place renumbering is ambiguous.

## 4. Phase 1 — Convert to `pedigree_id` as the canonical identifier

- `pedigree_id` **becomes the `id`** everywhere: `horses_data.json`, Hive keys, sire/dam relationships. The old arbitrary local id (1–143) is retired.
- Relationships are then trivial: `sire_id`/`dam_id` *are* pedigree ids; the family tree resolves with no indirection.
- _(Deferred: a reserved id range for app-created horses the website hasn't catalogued. Not needed now — the app only annotates existing catalogued horses; new foals arrive via re-scrape. Revisit only if we add a "log an uncatalogued horse" feature.)_

### Flow 2 — how her device survives the cutover (deploy = GitHub Pages, auto-reaches her)
Hosting is **GitHub Pages** (free): a push updates the live site; her PWA picks it up via the service worker on next load. Her data lives in **browser IndexedDB (Hive)** and persists across code updates — a deploy never deletes it. The only danger is the **id-scheme mismatch** (old-keyed boxes vs new pedigree-keyed code). We handle it with a **device overwrite at cutover**, which is safe *because* her data was already captured + baked into canon (§3d):

- Add a **`data_version` flag** in Hive. The cutover build bumps it.
- **Schema change (one-time cutover):** on boot, version bump detected → **clear all boxes and reload the fresh pedigree-keyed bundled data** (which now contains her integrated canon). No in-app key-remap, no manual re-import.
- **Content update (every later deploy):** version bump → **reload the canon/book box only; leave her user boxes untouched.** This is also the fix for today's bug where new horses never reach existing users (book data only loads when the box is empty — [data_service.dart:30](horse_app/lib/services/data_service.dart#L30)). A post-cutover "add foals" deploy must **never** wipe the local data she's collected since.
- **Deleted horse (deceased) + existing local data:** harmless. The app only renders horses present in canon, so any orphaned user data keyed to a removed horse simply never displays — no crash, no corruption. _(Orphaned blobs linger in storage; optional future "prune orphans" pass. A future "Departed" section could resurface a user's own data on departed horses.)_

**Lossless conditions:** (1) one final export immediately before the cutover, with a brief freeze on adding data; (2) **personal notes** — since notes are local-only (never canon, §0.1), the cutover's box-wipe would drop them, so we **remap her notes old→pedigree id and re-import once** after the overwrite (her photos/herd return automatically via canon). If her notes are throwaway, we may skip this — decide once we see the volume. **During the collection phase, deploy only non-schema changes**; the id cutover is a deliberate, coordinated event.

## 5. Schema changes (`horses`)

Existing columns stay. `id` is repurposed to hold pedigree_id. New columns (all nullable, additive):
`state` (VA/MD), `region`, `coat_pattern`, `markings`, `genotype`, `birth_location`, `breeder`, `owner`, `auction_number`, `registry`, `registry_number`, `sire_id`, `dam_id`, `dsc_photo_url` (copyrighted gallery link-out).

**Herd hierarchy:** `state` = VA (Chincoteague/CVFD) | MD (Assateague/NPS), from the website. `region` = `northern` | `southern`, **VA only** — Kristina's observational sub-herd split (not on the website); **MD horses have `region = null`** (the MD herd isn't subdivided). The old `herd` column (free-text, currently unused) is superseded by `state`+`region`. Kristina's backup `herd` values (`southern`×35, `northern`×26) map into `region`.

_(No `life_status` column: the canonical dataset is current VA/MD herds only. When a re-scrape finds a horse moved to the website's Past view, the changeset proposes a **deletion** rather than a status flip.)_

`horse_photos` gains a **`credit`** column (e.g. `K. Kent`) and its `source` token for our new photos changes from `user` → `field` (book photos stay `book`). App photo-priority + the model/`fromMap` update accordingly.

New `horse_markings` table (`horse_id`, `marking`) for marking-based search. Progeny/siblings are **derived by query** (`WHERE sire_id=? OR dam_id=?`) — no extra tables, no card clutter.

## 6. Curation & update tooling (the reviewable pipeline)

Both recurring jobs — ingesting Kristina's backup and re-scraping the website — reduce to the **same shape**: a source produces a **changeset** of proposed items; we review each item Accept/Reject; accepted items merge into the authoring DB; assets rebuild.

```
SOURCE → CHANGESET → review (Accept/Reject) → MERGE → BUILD app assets
  ├─ ingest K's backup.json → {new photos+YOLO crops, bands, herds, notes}
  └─ re-scrape website       → {new horses, departed→past, changed fields}
```

**Three separated layers** (matters because the app gets sold):
- **Authoring DB** (`horses.db`) — source of truth, lives only on this machine.
- **Curator console** (`tools/curator/`, **Flask**, localhost) — build-time review tool, **never ships** in the app.
- **The app** — only ever consumes built assets (`assets/horses_data.json` + `assets/photos/`).

**Changeset format:** a list of typed items (`photo` | `field_change` | `new_horse` | `departed`), each carrying before/after + provenance. The console renders each per type: photo crops original↔cropped side-by-side; field changes as old/new diffs; new/departed horses as cards. Buttons: Accept / Reject / (Re-crop | Edit); plus bulk "accept all". On **Merge**, accepted items write to `horses.db`.

**Workflow division ("smooth for you and I"):** I run the command (`ingest <backup.json>` or `scrape`) → it builds the changeset and launches the console → you click through visually → Merge → I rebuild assets. On-demand, repeatable; no fixed schedule (re-scrape whenever, more often than yearly is fine).

### Build pipeline (reproducible — including the currently-missing DB→JSON step)
1. `scrape_pedigrees.py` — fetch VA+MD Current rosters; for each id fetch `pedigree.php`, **cache raw HTML**, throttle ~1.5 s.
2. `parse_pedigree.py` — grammar parser → structured fields + marking tokens + sire/dam ids.
3. `make_changeset.py` — diff scrape/ingest against authoring `horses.db` → changeset for the console.
4. `build_assets.py` — after merge, write/refresh `horses.db` → regenerate `assets/horses_data.json` (keyed by pedigree_id) + copy photo assets.
   - **MERGE semantics (critical for updates):** canon photos/bands/herds (from Kristina) are keyed by pedigree_id and must be **preserved/merged** on every re-scrape — scraping refreshes public fields only, never clobbers our unique content.
5. Validation: every current-herd pony present; spot-check 5 end-to-end; confirm Kristina's remapped data round-trips.

## 7. App changes (Flutter)

- `horse.dart` — new fields in model/`fromMap`/`toMap`/`copyWith`.
- `data_service.dart` — load new fields; `state` (VA/MD) filter; marking search; family resolver by id; **user-photo-primary** ordering (flip `getFirstPhotoForHorse` to prefer `source != 'book'`). **Add `data_version` handling on `init()`:** schema bump → clear all boxes + reload bundled canon (one-time cutover); content bump → reload canon/book box only, preserve user boxes (replaces today's empty-box-only load gate).
- `horse_list_screen.dart` — VA/MD toggle (top level); within VA, a northern/southern `region` filter (MD shows a flat list, no region); marking filter chips; graceful empty-photo tiles. (No departed/past filter — departed horses aren't in the dataset.)
- `horse_detail_screen.dart` — show markings/pattern/genotype/registry; single tappable **Family** row → tree; keep video/pedigree links; photo gallery with K's photos first.
- New family tree screen (current-herd nodes clickable; others plain names).

## 8. Photos, family tree & licensing

- **Book photos (280):** kept, `source='book'`, demoted to secondary. Never deleted.
- **Kristina's photos:** YOLO-cropped, **watermarked + attributed to K. Kent** (§3c.1), `source='field'` with `credit='K. Kent'`, **primary** image — this is the "slowly replace book photos" path and prepares the photos as sellable, credited assets.
- **Departed horses:** **deleted from the canonical current dataset** (consistent with the update paths — the new build ships current VA/MD herds only). The 6 departed horses now in the app go away too. ⚠️ **Gate:** before deleting, the K-ingest changeset must surface any of her data (photos/bands/notes) attached to those 6 for keep-or-discard review — we decide once we see her backup. **Future option** (not now): if the app ever carries departed horses, they live in an **isolated "Departed" section**, integrated with the rest of the system *only* through the family tree — mirroring the website's separate Past-herd view.
- **Family tree:** **do not import dead/removed horses.** Ancestors not in current VA/MD herds (including the departed) show as plain non-clickable names; the tree dead-ends there.
- **DSC Photography galleries** & **identifyingchincoteagueponies.com videos:** copyrighted → **link out only, never download/rehost.**
- **Pedigree text:** factual/public, maintainers invite contributions → scrape politely.

## 9. Phasing

0. **Build the curator console** (`tools/curator/`, Flask) — the reviewable changeset/merge pipeline. First use case: ingest K's backup (capture → YOLO-crop+watermark → click-through accept/reject → merge), including the data-on-departed-horses keep/discard gate, plus offline ID-remap into canon. _(needs the backup file)_
1. Convert system to pedigree_id; rebuild assets with K's data baked in; deploy the cutover build — her device self-overwrites on the `data_version` bump (no manual restore).
2. Wire the re-scrape source into the same console; add 11 missing VA ponies; delete departed horses; surface enrichment fields on detail screen.
3. Markings search.
4. MD herd + VA/MD toggle.
5. Family tree navigation.
6. Polish (DSC link-out, device-photo replacement UX, history-blurb groundwork for sale).

## 10. Resolved decisions & pending input

Resolved:
- **Crop buffer** — 6% of box dims, clamped to image (tunable later).
- **Crop model** — stock `yolov8m.pt`.
- **Departed horses** — **delete** from the canonical dataset (no `life_status`), consistent with the update paths. Any future departed-horse support lives in an isolated "Departed" section, integrated only via the family tree. Gated by the K-data keep/discard review.
- **Uncatalogued-horse id range** — deferred (not needed unless we add an "add a horse" feature).

Pending input (tomorrow, with K's backup):
- **Notes** — confirmed **personal/local, never canon** (§0.1). Only open call: preserve them through the cutover (remap + one re-import) vs. treat as disposable — based on how many/how useful they are.
- **Data attached to the 6 departed horses** — keep anything valuable before deletion.

_No remaining blockers to start Phase 0 the moment the backup file lands._
