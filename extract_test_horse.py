
# extract_test_horse_fixed.py
import fitz  # PyMuPDF
from pathlib import Path

PDF_PATH = r"C:\Users\Workstation\Desktop\23cc6d_08d053fa21d8458eb748d7183afb17a4.pdf"
DATA_PAGE = 14          # data page for Tow Teagues Taco
PHOTO_PAGE = DATA_PAGE + 1

# Folder for extracted photos
PHOTO_DIR = Path("extracted_photos")
PHOTO_DIR.mkdir(exist_ok=True)

doc = fitz.open(PDF_PATH)

# === 1. Better text extraction from data page ===
print(f"{'='*80}")
print(f"PAGE {DATA_PAGE} — HORSE DATA")
print(f"{'='*80}\n")
page_data = doc[DATA_PAGE-1]
text = page_data.get_text("text")
print(text)

# Also show structured blocks (helps us see where the name might be hiding)
print(f"\n{'='*40} BLOCKS {'='*40}")
for block in page_data.get_text("dict")["blocks"]:
    if block.get("type") == 0:  # text block
        print(block["lines"][0]["spans"][0]["text"] if block["lines"] else "(empty)")

print(f"\n{'='*80}\n")

# === 2. Extract the two large photos from the photo page ===
print(f"Extracting 2 photos from PAGE {PHOTO_PAGE}...")
page_photo = doc[PHOTO_PAGE-1]
images = page_photo.get_images()   # ← fixed: removed rect=True

for idx, img in enumerate(images):
    xref = img[0]
    base_image = doc.extract_image(xref)
    image_bytes = base_image["image"]
    ext = base_image["ext"] or "jpg"
    
    filename = PHOTO_DIR / f"tow_teagues_taco_photo{idx+1}.{ext}"
    filename.write_bytes(image_bytes)
    print(f"   ✅ Saved: {filename.name}  ({len(image_bytes)/1024:.1f} KB)")

doc.close()
print(f"\n✅ Done! Check the new folder 'extracted_photos' next to your scripts")
