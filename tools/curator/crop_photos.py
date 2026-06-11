"""YOLO horse-crop + watermark for Kristina's photos (IMPLEMENTATION_PLAN.md §3c).

Step 2 of the curator ingest pipeline. Reads the originals that ingest_backup.py
extracted (out/normalized.json -> photos[].original_path) and, for each:

  1. Detect horses with stock yolov8m.pt (COCO 'horse' class).
  2. Pick the largest-area horse box.
  3. Expand it by a 6% buffer, clamped to image bounds (horse never touches the edge).
  4. Crop, bake a subtle "(c) K. Kent" visible watermark, write minimal EXIF
     (Artist/Copyright) -- full IPTC/XMP via exiftool is a later add (§3c.1).
  5. Write the shipped crop to out/photos_cropped/. ORIGINALS ARE NEVER TOUCHED
     (they stay archived in out/photos_original/ for re-crop/re-watermark later).
  6. No horse detected -> copy the original through unchanged, flagged for manual review.

The detection/crop pattern is borrowed (read-only) from the Drone_brain project's
perception/perception_node.py -- ultralytics horse capability only, no coupling.
This runs in the curator's OWN venv (tools/curator/.venv, py3.11); it never uses
Drone_brain's environment.

Usage (from the curator venv):
    tools/curator/.venv/Scripts/python crop_photos.py [--out OUTDIR] [--conf 0.25] [--buffer 0.06]
Writes out/photos_cropped/ and out/crop_manifest.json.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "out"
DEFAULT_MODEL = HERE / "models" / "yolov8m.pt"

HORSE_CLASS = "horse"          # COCO class name (id 17)
DEFAULT_CONF = 0.25            # ground-level tourist photos are clear; lower than drone's 0.40
DEFAULT_BUFFER = 0.06          # expand box 6% of its w/h, clamped (plan default)
CREDIT = "K. Kent"
WATERMARK_TEXT = f"© {CREDIT}"


def largest_horse_box(model, pil_img, conf):
    """Return (x1,y1,x2,y2, score) of the largest 'horse' box, or None.

    Pattern from Drone_brain perception_node.py: iterate r.boxes, read class via
    r.names[int(box.cls[0])], coords via box.xyxy[0].tolist().
    """
    results = model(pil_img, conf=conf, verbose=False)
    best = None
    best_area = 0.0
    for r in results:
        if r.boxes is None:
            continue
        for box in r.boxes:
            if r.names[int(box.cls[0])] != HORSE_CLASS:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            area = (x2 - x1) * (y2 - y1)
            if area > best_area:
                best_area = area
                best = (x1, y1, x2, y2, float(box.conf[0]))
    return best


def expand_and_clamp(box, w, h, buffer):
    """Expand a box by `buffer` of its own w/h, clamped to [0,w]x[0,h]. Returns ints."""
    x1, y1, x2, y2 = box[:4]
    dx = (x2 - x1) * buffer
    dy = (y2 - y1) * buffer
    x1, y1 = max(0, x1 - dx), max(0, y1 - dy)
    x2, y2 = min(w, x2 + dx), min(h, y2 + dy)
    return int(round(x1)), int(round(y1)), int(round(x2)), int(round(y2))


def _watermark_font(img_w):
    size = max(14, img_w // 45)  # scale to image; subtle
    for name in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def apply_watermark(crop):
    """Subtle bottom-right '(c) K. Kent', semi-transparent (~40%)."""
    crop = crop.convert("RGBA")
    overlay = Image.new("RGBA", crop.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    font = _watermark_font(crop.width)
    box = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    pad = max(6, crop.width // 120)
    x, y = crop.width - tw - pad * 2, crop.height - th - pad * 2
    # faint shadow for legibility on light coats, then the mark at ~40% opacity
    draw.text((x + 1, y + 1), WATERMARK_TEXT, font=font, fill=(0, 0, 0, 90))
    draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255, 102))
    return Image.alpha_composite(crop, overlay).convert("RGB")


def _exif_bytes(year):
    img = Image.new("RGB", (1, 1))
    exif = img.getexif()
    exif[0x013B] = CREDIT                                        # Artist
    exif[0x8298] = f"© {year} {CREDIT}. All rights reserved."  # Copyright
    return exif.tobytes()


def crop_all(out_dir, model_path, conf, buffer):
    from ultralytics import YOLO  # imported lazily so --help works without the venv

    normalized = json.loads((out_dir / "normalized.json").read_text(encoding="utf-8"))
    photos = normalized.get("photos", [])
    cropped_dir = out_dir / "photos_cropped"
    cropped_dir.mkdir(parents=True, exist_ok=True)
    exif = _exif_bytes(_dt.date.today().year)

    model = YOLO(str(model_path))
    manifest = []
    detected = no_horse = 0
    for p in photos:
        src = out_dir / p["original_path"]
        dst = cropped_dir / p["original_filename"]
        img = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        w, h = img.size
        box = largest_horse_box(model, img, conf)
        if box is None:
            # Keep original (watermarked) and flag — don't drop the photo.
            out_img = apply_watermark(img)
            crop_box = None
            score = None
            no_horse += 1
        else:
            crop_box = expand_and_clamp(box, w, h, buffer)
            score = round(box[4], 3)
            out_img = apply_watermark(img.crop(crop_box))
            detected += 1
        out_img.save(dst, "JPEG", quality=92, exif=exif)
        manifest.append({
            "pedigree_id": p["pedigree_id"], "name": p["name"],
            "filename": p["original_filename"],
            "cropped_path": str(dst.relative_to(out_dir).as_posix()),
            "horse_detected": box is not None, "detection_conf": score,
            "crop_box": crop_box, "orig_size": [w, h],
            "needs_review": box is None,
            "source": p["source"], "credit": p["credit"],
        })

    (out_dir / "crop_manifest.json").write_text(
        json.dumps({"conf": conf, "buffer": buffer, "model": model_path.name,
                    "count": len(manifest), "detected": detected, "no_horse": no_horse,
                    "photos": manifest}, indent=2, ensure_ascii=False),
        encoding="utf-8")
    return len(manifest), detected, no_horse, manifest


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    ap.add_argument("--conf", type=float, default=DEFAULT_CONF)
    ap.add_argument("--buffer", type=float, default=DEFAULT_BUFFER)
    args = ap.parse_args()

    if not (args.out / "normalized.json").exists():
        sys.exit(f"no normalized.json in {args.out} -- run ingest_backup.py first")
    if not args.model.exists():
        sys.exit(f"weights not found: {args.model}")

    total, detected, no_horse, manifest = crop_all(args.out, args.model, args.conf, args.buffer)
    print(f"cropped {total} photos (conf {args.conf}, buffer {args.buffer}, {args.model.name})")
    print(f"  horse detected: {detected} | no horse (kept original, flagged): {no_horse}")
    print(f"  -> {(args.out / 'photos_cropped')}")
    print(f"  -> {(args.out / 'crop_manifest.json')}")
    for m in manifest:
        tag = f"conf {m['detection_conf']}" if m["horse_detected"] else "NO HORSE - review"
        print(f"    {m['name'][:32]:32} {m['filename']:28} {tag}")


if __name__ == "__main__":
    main()
