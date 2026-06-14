# Chincoteague/Assateague Ponies App — Data Refresh, ID Conversion & Photo Pipeline

_Updated 2026-06-12. Source site: `chincoteaguepedigrees.com` (static HTML, ISO-8859-1). **Phases 0 + 1 DONE and DEPLOYED** — curator pipeline built, band fix shipped, hosting reconstructed, and the one-time `pedigree_id` cutover is live + verified on Kristina's device (2026-06-12). The app now runs on `pedigree_id` with her 21 photos / 49 bands / 61 regions / 5 notes in canon. **Next: Phase 2 website scrape** (roster completion + enrichment), blocked on the `herds.php` Current/Past toggle._

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

### 3a. Capture (smoothest path — no cable) — ✓ DONE
The app's built-in **Backup** (list screen → backup icon → Backup) calls `exportUserData()` and writes `chincoteague_backup_DATE.json` — a self-contained file with notes, herds, bands, photo metadata, **and every device photo base64-encoded**. Saved to Files/iCloud → project dir. (No iOS sandbox extraction needed.)
**✓ Received & gitignored:** `kristina_data/chincoteague_backup_2026-06-10.json` (33 MB, v1, exported 2026-06-10 20:16).

### 3b. Inspect & harvest to canon — ✓ INSPECTED (verified contents below)
Policy follows the architecture principle (§0.1):
- **Photos + band/region observations → harvested to canon** (K is the content source; this is the point of collection).
- **Notes → stay personal/local, never canon** — they remain only on K's device.

**Verified backup contents** (all 66 referenced horse ids valid → map cleanly to our 143):
- **61 region assignments** (`southern`×35, `northern`×26) → canon `region`.
- **44 band sightings** — mare→stallion, dated, multiple dates per mare; 5 stallions (Tornado's Legacy 15, Surfer's Riptide 12, Norman Rockwell Giddings 12, Thunderbolt 3, Beach Boy 2) → canon bands. _Note: predates the band-remove fix (§11), so some may be stale — prune in the console review._
- **15 photos** (~13 horses), full-res 12 MP (4032×3024), JPEG/MPO → crop+watermark to canon.
- **5 notes** (stay local): Winter Moon (died), Gidget's Beach Baby (passed), CLG Pennies From Heaven (vet care PA), Joe's Spirit (roadside incident), Shy & Sassy Sweet Lady Suede (eye injury). Valuable enough to **preserve through the cutover** (§4).

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

**Framing — one-time bridge vs. the recurring loop (important):** the cutover is **not** one of the recurring update jobs. It is a single, structural **identifier migration** (arbitrary local id 1–143 → website `pedigree_id`) that happens **once, ever**, then never again. The recurring jobs — **ingest her backup** (harvest new photos/bands/regions, run whenever she's collected a batch) and **re-scrape the website** (add newborns / remove departed / refresh fields, run whenever the roster changes) — are the steady state; both are non-destructive "content updates" that preserve her local boxes. We pay the id flip once so every recurring run afterward has a stable, website-shared key (re-scrape matches by pedigree_id; relationships/family tree are pedigree_id; harvested data stays attached to the same horse across roster churn) instead of maintaining a fragile local↔pedigree mapping forever. **Do the flip soon, while her on-device data is still small** (64 herd assignments, 44 bands, 15 photos, 5 notes) — every month of collection makes the one-time device reload carry more. Bundle the flip with deploying this first harvest.

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
`state` (VA/MD), `region`, `coat_pattern`, `markings`, `genotype`, `birth_location`, `breeder`, `owner`, `auction_number`, `registry`, `registry_number`, `sire_id`, `dam_id`, `dsc_photo_url` (copyrighted gallery link-out), **`background`** (canon narrative — see below).

**`background` supersedes `book_info` (decided 2026-06-12).** The old `book_info` blurb is a *subset of the website description prose* (verified: Daisey's `book_info` is byte-identical to the trailing sentences of her `pedigree.php` description) and exists for only 23/143 horses. So: **drop the "From the Book" display**, and have `parse_pedigree.py` capture the **residual narrative** (the prose left after the structured fields are extracted — donation stories, "Alternate sire/dam", "descends from Misty 7 times", nicknames like "Queen Neptune") into a canon **`background`** field. Shareable (every buyer gets it), refreshes with each scrape, absorbs all of `book_info`. `book_info` column joins the build-cruft drop list. Genuinely unique-to-Kristina observations stay in her local Notes.

**`coat_pattern` is a FILTER field, not a display row (decided 2026-06-12).** Since `color` comes from the roster already as common usage ("bay pinto"), a separate "Pattern: pinto" row is redundant — the detail card folds pattern into the color line and does not show a standalone pattern row. `coat_pattern` (normalized `tobiano→pinto`) earns its keep as a **filter/search** dimension, not card text.

**Pedigree-chart flag codes (NOT in the prose paragraph — easy to miss).** Each name in the `pedigree.php` 4-gen chart carries optional flags; legend: **M** Misty descendant · **B** buyback · **F** feral · **★** full sibling · **H** half Chincoteague. Capture **M/B/F/H** as four additive boolean columns (`misty_descendant`, `buyback`, `feral`, `half_chincoteague`) in the Phase 2 scrape and show them as small badges on the detail card. The explicit **B** flag supersedes inferring buyback from `buyback_donor`. **★ (full sibling) is NOT scraped — derive it:** in the family resolver, both `sire_id`+`dam_id` match = full sibling (★), one matches = half. The current book-derived data has none of these flags.

**Herd hierarchy:** `state` = VA (Chincoteague/CVFD) | MD (Assateague/NPS), from the website. `region` = `northern` | `southern`, **VA only** — Kristina's observational sub-herd split (not on the website); **MD horses have `region = null`** (the MD herd isn't subdivided). The old `herd` column (free-text, currently unused) is superseded by `state`+`region`. Kristina's backup `herd` values (`southern`×35, `northern`×26) map into `region`.

`region` is **mutable, in-flux observational data** (wild horses move N↔S), shipped as a **dated canon snapshot** refreshed semi-annually with the scrape; end users can locally override it between releases (§0.1), and Kristina's overrides are harvested into the next snapshot. **Design choice:** store a `region_observed` date alongside `region` (backfill existing assignments with the backup's export date, 2026-06-10) so freshness is visible — recommended, since the data's whole point is tracking movement. Bands already carry dates; this makes region consistent.

_(No `life_status` column: the canonical dataset is current VA/MD herds only. When a re-scrape finds a horse moved to the website's Past view, the changeset proposes a **deletion** rather than a status flip.)_

`horse_photos` gains a **`credit`** column (e.g. `K. Kent`) and its `source` token for our new photos changes from `user` → `field` (book photos stay `book`). App photo-priority + the model/`fromMap` update accordingly.

New `horse_markings` table (`horse_id`, `marking`) for marking-based search. Progeny/siblings are **derived by query** (`WHERE sire_id=? OR dam_id=?`) — no extra tables, no card clutter.

### Field reference: today (book) → post-refresh (display design TBD later)

What a horse record holds now vs. what the refresh adds. (Display/layout is a separate, later discussion — this is just the data inventory.)

| Area | Today (book-derived, flat row) | Post-refresh | Origin |
|---|---|---|---|
| Identity | `id` (local 1–143), `name`, `nickname`, `qr_pedigree_url` | `id` = **pedigree_id**; name/nickname kept | re-key |
| Physical | `color`, `sex`, `brand`, `eye_color`, `birth_year`, `birth_date` | same, **+ `coat_pattern`, `markings`, `genotype`, `birth_location`** | website prose |
| Lineage | `sire`, `dam` (name strings only) | **+ `sire_id`/`dam_id`** (real pedigree links); names kept | chart links |
| Lineage flags | — | **`misty_descendant`, `buyback`, `feral`, `half_chincoteague`** (bool) | chart M/B/F/H |
| Provenance | `auction_price`, `buyback_donor`, `book_info` | **+ `breeder`, `owner`, `auction_number`, `registry`, `registry_number`** | website prose |
| Herd | `herd` (empty in canon) | **`state`** (VA/MD, website) on the row; `region` is its own dated section | roster / Kristina |
| Media | `qr_video_url` | **+ `dsc_photo_url`** (link-out) | website |
| Build cruft | `book_page`, `pdf_page_data`, `pdf_page_photo` | **dropped** at cutover | — |
| **Photos** (separate) | `horse_photos`: 280 rows, all `source='book'` | **+ field crops** (`source='field'`, `credit='K. Kent'`), field-first | Kristina |
| **Bands** (separate) | — (none in canon; local-only today) | **`bands[]`** dated mare→stallion | Kristina |
| **Regions** (separate) | — | **`regions[]`** dated N/S | Kristina (not website) |
| **Derived** (stored nowhere) | — | progeny, siblings (**full ★ vs half** via parent match), family tree, marking search | query |

Three origins, three lifecycles: **website public fields** refresh every scrape; **Kristina's canon** (photos/bands/regions) is preserved across scrapes; **derived views** are computed on demand. Post-scrape rows are richer but **unevenly populated** — each field fills only when that horse's page states it (e.g. MD/NPS ponies: NPS registry, no auction/buyback; `region` is always Kristina-only).

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
4. `build_assets.py` — **✓ SCAFFOLDED.** Reads `horses.db` → `horses_data.json` in the decided shape; re-keys horses local→pedigree (by lookup), assembles `horses`/`photos`/`bands`/`regions`. **Safe by default** — writes to `tools/curator/out/build/` (dry run); `--out ../../horse_app/assets` to deploy. Handles canon tables being absent (empty sections pre-merge). Dry-run verified on real data: 143 horses, 0 id collisions (local-42 → pedigree-3), 280 book photos remapped, 0 orphans. **Remaining (Phase 1/2):** `sire_id`/`dam_id` stay null until the scrape resolves pedigree links; §5 enrichment columns emit null until added + scraped; book photo files copied only on real deploy; the app-side loader must learn to read `bands[]`/`regions[]` (see §7).
   - **MERGE semantics (critical for updates):** canon photos/bands/herds (from Kristina) are keyed by pedigree_id and must be **preserved/merged** on every re-scrape — scraping refreshes public fields only, never clobbers our unique content.
   - **Built asset shape (decided):** `horses_data.json` keeps **separate, top-level, pedigree-keyed sections** rather than embedding the dated data inside each horse — chosen because the recurring re-scrape churns `horses[]` (add newborns, drop departed), and separate sections make add = append, delete = filter + prune dangling refs, without disturbing our unique canon:
     - `horses[]` — `id` = pedigree_id; `sire_id`/`dam_id` (was name strings); enriched fields from §5 (`state`, `coat_pattern`, `markings`, `genotype`, `breeder`, `owner`, `auction_number`, `registry`, `registry_number`, `dsc_photo_url`). **`region` is NOT here** (it's dated → its own section).
     - `photos[]` — `{horse_id, filename, source, credit}`; Kristina's field crops (`source:"field"`, `credit:"K. Kent"`) sort ahead of `book`; cropped files copied into `assets/photos/`.
     - `bands[]` — `{mare_id, stallion_id, date_recorded}` (dated, from `bands` table).
     - `regions[]` — `{id, region, observed}` (dated/ephemeral, from `region_observations`).
   - **App-side overlay:** `bands[]`/`regions[]` load into **canon** boxes; the user's local edits overlay them at read-time, exactly as `getAllHorses()` already overlays user notes/herd onto canon ([data_service.dart:73-79](horse_app/lib/services/data_service.dart#L73-L79)). Extending that existing pattern to bands/regions is the "canon vs user box split."
5. Validation: every current-herd pony present; spot-check 5 end-to-end; confirm Kristina's remapped data round-trips.

### 🍞 Breadcrumbs — status & next steps (updated 2026-06-12, end of scrape-tooling session)

**Phases 0 + 1 are DONE and DEPLOYED** — app is live on `pedigree_id`, verified on Kristina's device 2026-06-12. **Phase 2 is UNBLOCKED and ~half built** — scraper, parser, and reconcile tooling are done & validated; the build/merge/app side is what's left. See the `phase2-scrape-progress`, `detail-card-design`, `phase1-cutover-done`, `pedigree-site-scraping`, and `ponies-app-deployment` memories.

**✅ Phase 2 progress this session (all on branch `phase1-pedigree-cutover`, committed, NOT pushed/deployed):**
- **Unblocked** — the `herds.php` "blocker" was a wrong URL: pages live under `/pedigree/`; POSTing to the bare root 404s + drops the body. All 4 rosters toggle fine (VA 148/411, MD 88/328).
- **`scrape_pedigrees.py`** — cached the 4 rosters + all 236 Current pedigree pages (raw HTML in `out/scrape/raw/`, gitignored; `out/scrape/rosters.json`). Resumable.
- **`parse_pedigree.py`** — FEATURE-COMPLETE parser → `out/scrape/parsed.json`. All §5 fields incl. `registry`/`registry_number`, `sire_id`/`dam_id`(+names), M/B/F/H flags, heterochromia-aware `eye_color`, and the canon **`background`** narrative (replaces book_info; 69/236). `--validate`, `--id N`.
- **`reconcile.py`** — app-vs-scrape diff. Validation: sex 137/137, birth_year 137/137, sire 133/136, dam 124/137; **zero genuine conflicts** (apparent ones are nickname aliases, auto-resolved).
- **Roster diff** (matches plan): **11 new VA, 88 new MD, 6 departed** (all in VA-Past; keep/discard gate CLEAN — 0 canon data attached, safe to delete).
- **Detail-card redesign + data decisions** locked (see `detail-card-design`): single continuous "ID card", collapsible tiers; `coat_pattern`=filter-not-row; drop book_info→`background`; region history hidden (DB only); editability preserved.
- **Phase 7 (YouTube video ingest)** specced as a future curator source (§8.1).

✅ **Completed this cycle:**
0. **Hosting reconstructed** (was lost): repo `omegamanndrone/chincoteague-ponies`, Pages source = `gh-pages` branch root, deploy = `flutter build web --base-href /chincoteague-ponies/` then push the contents of `build/web` to `gh-pages` (a git repo lives in `build/web/.git` pointing there). **Band fix `77552ea` shipped + verified** (her data produced a `status:left` marker = proof it works).
1. **Final backup harvested** — 2026-06-12 export → `ingest_backup` → `crop_photos` (YOLO + © K. Kent, now height-based watermark) → console review → `merge`. Kristina accepted **21 photos** (rejected 4 tiny/blurry), **49 bands**, **61 regions**, 5 notes.
2. **`build_assets --out ../../horse_app/assets`** — final pedigree-keyed assets; regions deduped to the **current** snapshot (DB keeps dated history). Emits the 4 lineage-flag columns (null) + `id_remap.json`.
3. **Phase 1 cutover DEPLOYED.** `DataService` is version-gated: `schemaVersion=1` wipe+reload canon + **in-app notes remap** (via non-personal `id_remap.json` — notes never published); `contentVersion` = reload-canon-only (preserves user boxes). Canon∪local overlays for bands + regions; photo priority field-first (+ render `field` source from assets); **provenance accent** (thin teal left rule on local-only data, §10); region surfaced on the detail "Herd" button. `test/migration_test.dart` green. Her device migrated cleanly — photos/bands/herd-N/S/notes all survived.

🔜 **Phase 2 status — the scrape MERGE pipeline is DONE & verified (2026-06-13); only the app side + the real merge remain.** Steps 1–4 below are ✅ built and proven end-to-end on a throwaway DB copy (authoring `horses.db` left pristine — the real merge waits for Kristina's console review). Confirmed with user: scraped data lands in a new pedigree-keyed `scraped_horses` table overlaid at build (not by altering the book table); conflicts auto-resolve to the website but stay listed; **sex ships mare/stallion** (build maps the website's female/male).
1. ✅ **`make_changeset.py --source scrape`** — diffs `parsed.json` + `rosters.json` vs `horses.db` → **121 review items** (`field_change` ×16 [color×3/dam×7/brand×6, all website-more-correct], `new_horse` ×11 VA + ×88 MD, `departed` ×6 [gate CLEAN]) + embeds 236 normalized records. Auto-accepts `same`/`spelling`/`alias`; reject a `field_change` ⇒ merge nulls that scrape col ⇒ book value survives (don't-clobber). Reuses the now source-aware Flask `console.py`.
2. ✅ **`normalize.py`** — shared `tobiano→pinto` + roster-color-as-canonical + sex + bucket; `reconcile.py` refactored to import it.
3. ✅ **`merge.py` (`merge_scrape`)** — writes `scraped_horses` (236) + `departed_horses` (6), additive/pedigree-keyed, honoring review decisions; a full re-scrape replaces the tables (idempotent).
4. ✅ **`build_assets.py` (`merge_horse`)** — overlays scrape on book with **don't-clobber** (verified: book brands 22/19 survive where scrape null); drops `book_info`, emits `background`, resolves `sire_id`/`dam_id`, +99/−6, normalizes sex (mare/stallion) / color (title-case) / `$`-price / markings (joined string). Dry-run: **236 horses, 290 photos (departed's 11 book photos dropped), 49 bands, 61 regions.**
5. 🔜 **App side (NEXT)** — `horse.dart` gains `background` + drops `bookInfo`; `horse_detail_screen.dart` rebuilt to the new ID card (`detail-card-design`); gate region UI on `state != 'MD'`; markings display. `state` filter + markings search land in their own phases (3–4). Then real merge (after K reviews — first clear the stale ingest `review_state.json`) → `build_assets --out ../../horse_app/assets` → ship as a **CONTENT update** (non-schema) preserving all of K's local data, matched by `pedigree_id`.

**Parked (safe to defer):**
- **Watermark / tiny-crop quality** — `WATERMARK_FRAC` in `crop_photos.py` sizes by height now (consistent ~4.5%); 3–4 genuinely tiny/low-res crops still look big (image quality, not watermark). Re-crop + redeploy anytime (originals archived) as a content update.
- **VA/MD toggle + region filter UI** (Phase 4) — region data is in canon; only the detail "Herd" button surfaces it so far.
- **Branch hygiene** — all work on `phase1-pedigree-cutover` (pushed to origin); `master` still at the band fix. Merge whenever; does NOT affect the live site (serves from `gh-pages`).

**~~Open question~~ RESOLVED:** visual canon-vs-user cue → thin left accent rule on local-only items, one reserved accent color app-wide (§10). Non-blocking polish.
**Open with Kristina:** her collection workflow. _(The 2 region gaps — Pappy's Pony, Angelique's Tigress Warrior, both VA — are RESOLVED: Kristina doesn't know their N/S yet, so they stay unassigned and she adds a region during ongoing collection. The app already supports this for VA horses — an unassigned VA horse shows an "Assign Herd" button. **MD ponies get NO region** — app TODO: hide the region UI for `state == 'MD'`, see §7.)_

## 7. App changes (Flutter)

- `horse.dart` — new fields in model/`fromMap`/`toMap`/`copyWith`.
- `data_service.dart` — load new fields; `state` (VA/MD) filter; marking search; family resolver by id; **user-photo-primary** ordering (flip `getFirstPhotoForHorse` to prefer `source != 'book'`). **Add `data_version` handling on `init()`:** schema bump → clear all boxes + reload bundled canon (one-time cutover); content bump → reload canon/book box only, preserve user boxes (replaces today's empty-box-only load gate).
- `horse_list_screen.dart` — VA/MD toggle (top level); within VA, a northern/southern `region` filter (MD shows a flat list, no region); marking filter chips; graceful empty-photo tiles. (No departed/past filter — departed horses aren't in the dataset.)
- `horse_detail_screen.dart` — **redesigned as ONE continuous "ID card" (hybrid: glanceable, with collapsible low-value tiers), decided 2026-06-12.** Top→bottom:
  - **At-a-glance identity (always open):** sex · color (roster's "bay pinto", pattern folded in — no separate pattern row) · age/birth year · current `region`; the M/B/F/H flags + `registry` rendered as **small badges**, not rows. **Region is VA-only** — for `state == 'MD'` ponies, show **no region line and no "Assign Herd" button** (the MD herd isn't subdivided into N/S; an unassigned VA horse still gets the button). _App TODO: gate the region UI on `state != 'MD'` once MD ponies land._
  - **DESCRIPTION (always open):** `markings` (the field-ID core), eye color, brand. This is the most prominent descriptive block.
  - **BANDS (always open, prominent):** current band + history (last 2 yrs) — Kristina's editable observational data, provenance-accented.
  - **▸ Pedigree / Family (collapsed):** sire/dam tappable → family tree.
  - **▸ Records & registry (collapsed):** breeder, owner, full birth date+location, auction $+#, buyback donor, registry+#, **genotype** (technical, lives here).
  - **▸ Background (collapsed):** the canon `background` narrative (replaces "From the Book", which is dropped).
  - **Your Notes (always open, editable)** + a **compact link row** (video · pedigree · DSC link-out).
  - **Region *history* is NOT displayed** — kept in the DB backend only (single-entry for most horses; the *current* region shows in the identity line). Rare cross-herd (MD→VA) moves the region model can't express go in Notes as free text.
  - **Editability is unchanged from today:** bands, region/herd, notes, photos stay user-editable (local overlay); all scraped/canon fields are **read-only on-device** (corrections happen at the curator gate, §10), so a content update never clobbers the user's edits.
- New family tree screen (current-herd nodes clickable; others plain names).

## 8. Photos, family tree & licensing

- **Book photos (280):** kept, `source='book'`, demoted to secondary. Never deleted.
- **Kristina's photos:** YOLO-cropped, **watermarked + attributed to K. Kent** (§3c.1), `source='field'` with `credit='K. Kent'`, **primary** image — this is the "slowly replace book photos" path and prepares the photos as sellable, credited assets.
- **Departed horses:** **deleted from the canonical current dataset** (consistent with the update paths — the new build ships current VA/MD herds only). The 6 departed horses now in the app go away too. ⚠️ **Gate:** before deleting, the K-ingest changeset must surface any of her data (photos/bands/notes) attached to those 6 for keep-or-discard review — we decide once we see her backup. **Future option** (not now): if the app ever carries departed horses, they live in an **isolated "Departed" section**, integrated with the rest of the system *only* through the family tree — mirroring the website's separate Past-herd view.
- **Family tree:** **do not import dead/removed horses.** Ancestors not in current VA/MD herds (including the departed) show as plain non-clickable names; the tree dead-ends there.
- **DSC Photography galleries** & **identifyingchincoteagueponies.com videos:** copyrighted → **link out only, never download/rehost.** (Card label: **"Photos at DSC"**, not a bare "DSC".)
- **Pedigree text:** factual/public, maintainers invite contributions → scrape politely.

### 8.1. Kristina's YouTube videos — a future "video ingest" curator source (decided as a later phase, 2026-06-12)
Kristina has a YouTube channel with many videos of these ponies. Goal: replace the per-horse **"▶ video"** link (today → identifyingchincoteagueponies.com) with **her own** video when one exists, falling back to the existing link otherwise — the same primary-with-fallback model as her field photos.

**Architecture (the non-negotiable part): index at BUILD time, never from the app.** The app must never call the YouTube API at runtime (would ship an API key in the client, hit quotas, break offline/PWA, and couple the sold app to her account). Instead it's a **third recurring curator source** that reuses the existing changeset → console → merge machinery (alongside photo-ingest and the website scrape):

```
K's YouTube channel ─(YouTube Data API, our machine)─▶ changeset (proposed horse↔video matches) ─▶ K reviews/confirms ─▶ bake youtube_url(s) into canon ─▶ ship
```

- **Matching — don't rely on hashtags alone.** The API gives each video's **title + description + tags**; run all three through the **name/nickname resolver we already built** for the scrape (normalized names + roster nicknames). Most videos already name the horse in the title → likely matches with zero hashtagging. Hashtags become a booster for ambiguous cases, not a requirement on K.
- **Disambiguation = reviewable default, not a hard rule.** Auto-rank candidate videos per horse (the user's heuristic — *fewest other horse-matches = most horse-specific* — is a fine default order), but K **confirms/overrides** the primary in the console (same Accept/Reject flow as photos), killing false-match risk. Store a **short list** per horse (primary on the card + a "more videos" affordance), so a multi-horse compilation correctly appears as a secondary on each featured horse's card.
- **Schema:** a dated/credited `videos[]` canon section keyed by pedigree_id (`{horse_id, youtube_url, is_primary}`), parallel to `photos[]`/`bands[]`/`regions[]`. The card's video link prefers a primary `videos[]` entry, else `qr_video_url`.
- **Prereqs:** a YouTube Data API key (build-time only) + a new `ingest_youtube.py` curator source. Link out to YouTube (don't embed/rehost) to stay consistent with the link-out policy; her own videos are her copyright, so linking is clean.

## 9. Phasing

**Prerequisite (do before/alongside Phase 0): fix the band-remove bug (§11).** It's a non-schema change, safe to deploy during collection, and keeps Kristina's *ongoing* band data clean for future harvests. (This backup predates it, so its band data gets pruned in the console review instead.)

0. **✅ DONE — Build the curator console** (`tools/curator/`, Flask) — reviewable changeset/merge pipeline. Ingested K's backup (capture → YOLO-crop+watermark → accept/reject → merge), departed-horse keep/discard gate, offline ID-remap into canon.
1. **✅ DONE (deployed + verified 2026-06-12)** — Converted system to pedigree_id; rebuilt assets with K's data baked in; deployed the cutover build — her device self-overwrote on the `schemaVersion` bump (notes remapped in-app, no manual restore).
2. **🔜 NEXT (UNBLOCKED 2026-06-12)** — Wire the re-scrape source into the same console; add 11 missing VA ponies + 88 MD; delete the 6 departed horses (gate clean); surface enrichment + the redesigned ID card (§7). _Scraper + parser + reconcile already built & validated; remaining = `background` capture, normalization-map module, `make_changeset.py`, merge → build → deploy as a content update._
3. Markings search.
4. MD herd + VA/MD toggle.
5. Family tree navigation.
6. Polish (DSC "Photos at DSC" link-out, device-photo replacement UX, history-blurb groundwork for sale).
7. **Video ingest (§8.1)** — index Kristina's YouTube channel at build time → reviewable horse↔video matches → bake `videos[]` into canon; per-horse video link prefers her video over the identifyingchincoteagueponies.com fallback. New curator source; reuses the changeset/console/merge machinery.

## 10. Resolved decisions & pending input

Resolved:
- **Crop buffer** — 6% of box dims, clamped to image (tunable later).
- **Crop model** — stock `yolov8m.pt`.
- **Departed horses** — **delete** from the canonical dataset (no `life_status`), consistent with the update paths. Any future departed-horse support lives in an isolated "Departed" section, integrated only via the family tree.
- **Uncatalogued-horse id range** — deferred (not needed unless we add an "add a horse" feature).
- **Notes** — **personal/local, never canon** (§0.1); the 5 are valuable (deaths/vet/injury) → **preserve through the cutover** (remap + one re-import).
- **Departed-horse data** (verified): only 2 of the 6 have any K data, both **notes documenting their deaths** (Winter Moon, Gidget's Beach Baby) — no photos/bands lost on deletion. Keep those 2 death-notes in our authoring changelog.
- **`region` dating** — add `region_observed` (recommended), backfill to 2026-06-10.
- **Band-remove fix approach** — option (b), dated departure marker (§11). **✓ DONE.**
- **Band/region = preserve all dated history** — keep every dated sighting/observation; the app surfaces *current* + truncates the card to the last 2 years. Curator **band default = Accept** (not reject-stale); "older sighting" entries are kept, not pruned.
- **No in-app delete for incorrect band entries** — corrections happen at our Curator review gate (Reject on ingest), not on-device. Keeps the app to add/depart only.
- **Built asset shape** — separate top-level pedigree-keyed sections (`horses`/`photos`/`bands`/`regions`), not embedded; app overlays user edits on canon (§6). Chosen for clean add/delete under recurring re-scrapes.
- **Cutover timing** — the one-time id flip is a single bridge, **not** a recurring job; do it **soon**, bundled with this first harvest, while on-device data is small (§4).
- **Visual canon-vs-user cue** — **YES, show it** (worth it for the sellable product), via a **thin left accent rule** (2–3px) on local-only items; canon stays clean. One reserved accent color used **only** for provenance, app-wide (cards, photo tiles, band rows), with a one-line legend. Reads off the existing `source` token (`book`/`field`=canon, `user`=local), so it rides on the photo-priority plumbing (near-zero cost). Doubles as a "not yet harvested to canon" signal for Kristina. Non-blocking polish — build alongside or after the Phase 1 plumbing.

**Phase 0 status:** curator pipeline BUILT — `ingest_backup` → `crop_photos` (YOLO + © K. Kent) → `make_changeset` → Flask `console` (review) → `merge` (additive, pedigree-keyed). 15 photos cropped (14 detected), 125 changeset items. Band-remove bug fixed (§11). Nothing merged yet — awaiting Kristina's review.

Pending:
- ~~**Visual canon-vs-user distinction**~~ — **RESOLVED (see §10 Resolved):** show it via a thin left accent rule on local-only items, one reserved accent color app-wide. Non-blocking polish.
- **Kristina's console review** is the gate before any real Merge — nothing reaches the authoring DB on defaults until reviewed + Merge clicked.
- ~~**Region gaps**~~ **RESOLVED** — Pappy's Pony & Angelique's Tigress Warrior (both VA) have no N/S because Kristina doesn't know it yet; they stay unassigned and she adds it during ongoing collection. The app already supports this for VA (unassigned VA horse → "Assign Herd" button). **MD ponies get no region at all** (not subdivided) — app TODO: hide region UI for `state == 'MD'` (§7).
- **Phase 2 blocker** — `herds.php` Current/Past toggle stopped responding to scripts; departed-detection (reads the Past view) must be solved before re-scrape deletions work (see `pedigree-site-scraping` memory).

## 11. Known bugs / fixes

- **Band "remove" doesn't work** (reported by Kristina — a horse that leaves a band can't be removed from the display). **Root cause:** `_editBand` ([horse_detail_screen.dart:197-203](horse_app/lib/screens/horse_detail_screen.dart#L197-L203)) only **adds** still-selected horses via `addToBand`; it never deletes deselected ones. `removeBandEntry()` ([data_service.dart:267](horse_app/lib/services/data_service.dart#L267)) exists but has **no callers**. Because `getCurrentBandMembers()` keeps the latest-dated entry per horse, the stale membership persists.
  - **✓ FIXED** (option b — dated departure marker). `addToBand` now records a `status` (`present`|`left`); new `markBandDeparture` writes a dated `left` marker; `getCurrentBandMembers` takes the latest entry per horse and excludes those whose latest is `left`. `_editBand` writes departure markers for deselected horses (never the stallion). `ingest_backup.py` is forward-compat (treats `left` as departure, not canon). Current backup unchanged (44 bands / 41 current). `flutter analyze` clean.
  - **Workflow (decided):** band "remove" = **departure, not delete** — keep ALL dated sightings; the app shows current + a History section truncated to the **last 2 years**. **No in-app hard-delete for incorrect entries** (dropped to avoid over-complication): bad entries are pruned by us in the **Curator console (Reject)** on ingest. The fits the sellable model: removing a *canon-shipped* band on-device must be a **local departure-override that survives content updates** (a hard delete would be restored when the canon box reloads).
