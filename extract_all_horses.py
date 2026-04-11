"""
Extract all horse data, photos, and QR codes from the Chincoteague Ponies PDF
into a SQLite database with structured fields and extensible schema.
"""

import fitz  # PyMuPDF
import sqlite3
import re
import os
from pathlib import Path
from PIL import Image
from pyzbar.pyzbar import decode as decode_qr
import io

PDF_PATH = "23cc6d_08d053fa21d8458eb748d7183afb17a4.pdf"
DB_PATH = "horses.db"
PHOTO_DIR = Path("horse_photos")
PHOTO_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------

def create_db(db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS horses (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            name           TEXT NOT NULL,
            nickname       TEXT,
            color          TEXT,
            sex            TEXT,
            brand          TEXT,
            birth_year     TEXT,
            birth_date     TEXT,
            eye_color      TEXT,
            auction_price  TEXT,
            buyback_donor  TEXT,
            sire           TEXT,
            dam            TEXT,
            herd           TEXT,
            notes          TEXT,
            book_info      TEXT,
            qr_video_url   TEXT,
            qr_pedigree_url TEXT,
            book_page      INTEGER,
            pdf_page_data  INTEGER,
            pdf_page_photo INTEGER
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS horse_photos (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            horse_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            source   TEXT DEFAULT 'book',
            FOREIGN KEY (horse_id) REFERENCES horses(id)
        )
    """)
    # Comparison chart data (for reference)
    c.execute("""
        CREATE TABLE IF NOT EXISTS comparison_charts (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            color_group TEXT,
            pdf_page  INTEGER,
            raw_text  TEXT
        )
    """)
    # Close family index entries
    c.execute("""
        CREATE TABLE IF NOT EXISTS family_index (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            pdf_page INTEGER,
            raw_text TEXT
        )
    """)
    conn.commit()
    return conn


# ---------------------------------------------------------------------------
# QR code decoding
# ---------------------------------------------------------------------------

def decode_qr_image(image_bytes):
    """Decode a QR code from raw image bytes, upscaling if needed."""
    img = Image.open(io.BytesIO(image_bytes))
    # Try at original size first
    results = decode_qr(img)
    if results:
        return results[0].data.decode()
    # Upscale 4x with nearest neighbor to preserve QR sharpness
    big = img.resize((img.width * 4, img.height * 4), Image.NEAREST)
    results = decode_qr(big)
    if results:
        return results[0].data.decode()
    # Try 8x
    big = img.resize((img.width * 8, img.height * 8), Image.NEAREST)
    results = decode_qr(big)
    if results:
        return results[0].data.decode()
    return None


# ---------------------------------------------------------------------------
# Parse notes text into structured fields
# ---------------------------------------------------------------------------

def parse_notes_text(raw_notes):
    """Extract eye_color, auction_price, birth_date, buyback_donor from notes.
    Returns a dict with those fields plus 'book_info' for any remaining text."""

    text = raw_notes

    # --- Eye color ---
    eye_color = None
    eye_match = re.search(
        r'((?:One |Left |Right )?(?:\w+ )?(?:blue|brown|amber|hazel)(?:,? (?:one |and )?(?:\w+ )?(?:blue|brown|amber|hazel))?\s+eyes?\.?)',
        text, re.IGNORECASE
    )
    if eye_match:
        eye_color = eye_match.group(1).strip().rstrip('.')
        text = text[:eye_match.start()] + text[eye_match.end():]

    # --- Auction price ---
    auction_price = None
    # Handle multiple prices like "$3,500 (2023); $41,000 (2024)"
    price_match = re.search(
        r'Auction\s+price:\s*(\$[\d,]+(?:\s*\(\d{4}\))?(?:;\s*\$[\d,]+(?:\s*\(\d{4}\))?)*)\.?',
        text, re.IGNORECASE
    )
    if price_match:
        auction_price = price_match.group(1).strip()
        text = text[:price_match.start()] + text[price_match.end():]

    # --- Birth date (full date like "Born April 9, 2007" or "Born May 2004") ---
    birth_date = None
    born_match = re.search(
        r'Born\s+(\w+\s+\d{1,2},?\s+\d{4}|\w+\s+\d{4})\.?',
        text, re.IGNORECASE
    )
    if born_match:
        birth_date = born_match.group(1).strip()
        text = text[:born_match.start()] + text[born_match.end():]
    else:
        # "First seen" date as fallback
        seen_match = re.search(
            r'First\s+seen\s+(\w+\s+\d{1,2},?\s+\d{4})\.?',
            text, re.IGNORECASE
        )
        if seen_match:
            birth_date = "First seen " + seen_match.group(1).strip()
            text = text[:seen_match.start()] + text[seen_match.end():]

    # --- Buyback donor ---
    buyback_donor = None
    # Match "Buyback donor: Name." or "Buyback donors: Name1, Name2."
    # Also handle "Fall buyback." and "Sold at the ... auction"
    donor_match = re.search(
        r'Buyback\s+(?:donors?|donators?):\s*(.+?)(?=\.\s*[A-Z]|\.\s*$|$)',
        text, re.IGNORECASE | re.DOTALL
    )
    if donor_match:
        buyback_donor = donor_match.group(1).strip().rstrip('.')
        text = text[:donor_match.start()] + text[donor_match.end():]
    elif re.search(r'Fall\s+buyback\.?', text, re.IGNORECASE):
        buyback_donor = "Fall buyback"
        text = re.sub(r'Fall\s+buyback\.?\s*', '', text, flags=re.IGNORECASE)

    # --- Clean up remaining text as book_info ---
    # Remove "Sold at the ... auction" type info and keep it in book_info
    book_info = re.sub(r'\s+', ' ', text).strip()
    # Remove leading/trailing punctuation artifacts
    book_info = book_info.strip('. ')
    if not book_info:
        book_info = None

    return {
        'eye_color': eye_color,
        'auction_price': auction_price,
        'birth_date': birth_date,
        'buyback_donor': buyback_donor,
        'book_info': book_info,
    }


# ---------------------------------------------------------------------------
# Parse a data page's text into structured fields
# ---------------------------------------------------------------------------

def parse_data_page(text):
    """Parse the structured text from a horse data page."""
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]

    # Remove trailing boilerplate
    while lines and lines[-1] in ('NOT FOR RESALE', 'Table of Contents'):
        lines.pop()

    # Remove trailing page number (duplicate of first line)
    if len(lines) >= 2 and lines[-1].isdigit() and lines[0].isdigit():
        lines.pop()

    # First line is the book page number
    book_page = None
    if lines and lines[0].isdigit():
        book_page = int(lines.pop(0))

    # Find "Notes:" marker
    notes_start = None
    for i, line in enumerate(lines):
        if line == 'Notes:':
            notes_start = i
            break

    if notes_start is None:
        return None

    brand = birth_year = sex = sire = dam = color = name = nickname = None

    remaining = lines[notes_start + 1:]

    # Find brand line
    brand_idx = None
    for i, line in enumerate(remaining):
        if line.startswith('brand:'):
            brand_idx = i
            brand = line.replace('brand:', '').strip()
            break

    if brand_idx is None:
        return None

    # Raw notes text (between "Notes:" and "brand:")
    notes_lines = remaining[:brand_idx]
    raw_notes = ' '.join(notes_lines).replace('  ', ' ').strip()

    # Parse structured fields out of the notes text
    parsed = parse_notes_text(raw_notes)

    # Fields after brand
    after_brand = remaining[brand_idx + 1:]

    # birth year
    if after_brand and after_brand[0].startswith('birth year:'):
        birth_year = after_brand[0].replace('birth year:', '').strip()
        after_brand = after_brand[1:]

    # sex (mare, stallion, gelding)
    if after_brand and after_brand[0].lower() in ('mare', 'stallion', 'gelding'):
        sex = after_brand[0].lower()
        after_brand = after_brand[1:]

    # sire x dam
    if after_brand and ' x ' in after_brand[0]:
        parts = after_brand[0].split(' x ', 1)
        sire = parts[0].strip()
        dam = parts[1].strip()
        after_brand = after_brand[1:]

    # color
    if after_brand:
        color = after_brand[0]
        after_brand = after_brand[1:]

    # name
    if after_brand:
        name = after_brand[0]
        after_brand = after_brand[1:]

    # nickname (if anything left)
    if after_brand:
        nickname = after_brand[0]

    return {
        'name': name,
        'nickname': nickname,
        'color': color,
        'sex': sex,
        'brand': brand,
        'birth_year': birth_year,
        'birth_date': parsed['birth_date'],
        'eye_color': parsed['eye_color'],
        'auction_price': parsed['auction_price'],
        'buyback_donor': parsed['buyback_donor'],
        'sire': sire,
        'dam': dam,
        'book_info': parsed['book_info'],
        'book_page': book_page,
    }


# ---------------------------------------------------------------------------
# Extract QR codes from a data page
# ---------------------------------------------------------------------------

def extract_qr_codes(doc, page):
    """Extract QR code URLs from a data page.
    Returns (video_url, pedigree_url) or (None, None)."""
    images = page.get_images(full=True)
    qr_urls = []

    for img in images:
        xref = img[0]
        try:
            base = doc.extract_image(xref)
            w, h = base['width'], base['height']
            # QR codes are 70x70 PNGs
            if w <= 80 and h <= 80 and w == h:
                url = decode_qr_image(base['image'])
                if url:
                    qr_urls.append(url)
        except Exception:
            continue

    # Categorize: pedigree URLs vs video clip URLs
    video_url = None
    pedigree_url = None
    for url in qr_urls:
        if 'pedigree' in url.lower():
            pedigree_url = url
        elif '.mp4' in url.lower() or 'clip' in url.lower() or 'video' in url.lower():
            video_url = url
        elif not pedigree_url:
            # Default first unknown to pedigree
            pedigree_url = url
        else:
            video_url = url

    return video_url, pedigree_url


# ---------------------------------------------------------------------------
# Main extraction
# ---------------------------------------------------------------------------

def main():
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"PDF has {total_pages} pages")

    # Remove old DB if re-running
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = create_db(DB_PATH)
    cur = conn.cursor()

    horses_extracted = 0
    photos_extracted = 0
    qr_decoded = 0
    comparison_charts = 0
    family_entries = 0

    i = 0
    while i < total_pages:
        page = doc[i]
        n_images = len(page.get_images())
        text = page.get_text('text').strip()

        # --- Horse data page (6 images + Notes:) ---
        if n_images == 6 and 'Notes:' in text:
            data = parse_data_page(text)
            if data and data['name']:
                pdf_page_data = i + 1  # 1-indexed

                # Extract QR codes from this data page
                video_url, pedigree_url = extract_qr_codes(doc, page)
                if video_url or pedigree_url:
                    qr_decoded += 1

                # Insert horse record
                # notes is left NULL for user's own notes
                # book_info holds any remaining extracted text from the book
                cur.execute("""
                    INSERT INTO horses (name, nickname, color, sex, brand,
                        birth_year, birth_date, eye_color, auction_price,
                        buyback_donor, sire, dam, herd, notes, book_info,
                        qr_video_url, qr_pedigree_url,
                        book_page, pdf_page_data, pdf_page_photo)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    data['name'], data['nickname'], data['color'],
                    data['sex'], data['brand'], data['birth_year'],
                    data['birth_date'], data['eye_color'],
                    data['auction_price'], data['buyback_donor'],
                    data['sire'], data['dam'],
                    None,  # herd — user-entered
                    None,  # notes — user-entered
                    data['book_info'],
                    video_url, pedigree_url,
                    data['book_page'], pdf_page_data, None
                ))
                horse_id = cur.lastrowid

                # Look at next page for photos
                if i + 1 < total_pages:
                    next_page = doc[i + 1]
                    next_images = next_page.get_images()
                    if len(next_images) >= 1:
                        pdf_page_photo = i + 2
                        cur.execute("UPDATE horses SET pdf_page_photo = ? WHERE id = ?",
                                    (pdf_page_photo, horse_id))

                        # Extract photos
                        safe_name = re.sub(r'[^\w\s-]', '', data['name']).strip()
                        safe_name = re.sub(r'\s+', '_', safe_name).lower()

                        for idx, img in enumerate(next_images):
                            xref = img[0]
                            try:
                                base_image = doc.extract_image(xref)
                                image_bytes = base_image["image"]
                                ext = base_image.get("ext") or "jpg"
                                filename = f"{safe_name}_photo{idx+1}.{ext}"
                                filepath = PHOTO_DIR / filename
                                filepath.write_bytes(image_bytes)

                                cur.execute("""
                                    INSERT INTO horse_photos (horse_id, filename, source)
                                    VALUES (?, ?, 'book')
                                """, (horse_id, filename))
                                photos_extracted += 1
                            except Exception as e:
                                print(f"  Warning: could not extract image {idx} "
                                      f"for {data['name']}: {e}")

                        i += 1  # skip photo page since we just processed it

                horses_extracted += 1
                if horses_extracted % 20 == 0:
                    print(f"  ... {horses_extracted} horses extracted")

        # --- Comparison chart pages ---
        elif n_images == 0 and 'Comparison Chart' in text:
            chart_text = text
            if i + 1 < total_pages:
                next_text = doc[i + 1].get_text('text').strip()
                if 'Notable Details' in next_text or 'Legs' in next_text:
                    chart_text += '\n\n' + next_text
                    i += 1
            color_match = re.search(r'(\w[\w\s]*?) Comparison Chart', chart_text)
            color_group = color_match.group(1) if color_match else 'Unknown'
            cur.execute("""
                INSERT INTO comparison_charts (color_group, pdf_page, raw_text)
                VALUES (?, ?, ?)
            """, (color_group, i + 1, chart_text))
            comparison_charts += 1

        # --- Close Family Index ---
        elif 'Close Family Index' in text or 'Family Index' in text:
            cur.execute("""
                INSERT INTO family_index (pdf_page, raw_text)
                VALUES (?, ?)
            """, (i + 1, text))
            family_entries += 1

        i += 1

    conn.commit()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*60}")
    print(f"Horses extracted:       {horses_extracted}")
    print(f"Photos extracted:       {photos_extracted}")
    print(f"QR codes decoded:       {qr_decoded}")
    print(f"Comparison charts:      {comparison_charts}")
    print(f"Family index entries:   {family_entries}")

    cur.execute("SELECT COUNT(*) FROM horses")
    print(f"\nDB horse count:         {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM horse_photos")
    print(f"DB photo count:         {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM horses WHERE qr_video_url IS NOT NULL OR qr_pedigree_url IS NOT NULL")
    print(f"Horses with QR URLs:    {cur.fetchone()[0]}")

    # Show sample records with new fields
    print(f"\nSample records:")
    for row in cur.execute("""
        SELECT name, color, sex, eye_color, auction_price, birth_date,
               buyback_donor, sire, dam, book_info, qr_video_url, qr_pedigree_url
        FROM horses LIMIT 5
    """):
        print(f"\n  {row[0]} ({row[1]} {row[2]})")
        print(f"    Eye color:     {row[3]}")
        print(f"    Auction price: {row[4]}")
        print(f"    Birth date:    {row[5]}")
        print(f"    Buyback donor: {row[6]}")
        print(f"    Sire x Dam:    {row[7]} x {row[8]}")
        print(f"    Book info:     {row[9]}")
        print(f"    Video QR:      {row[10]}")
        print(f"    Pedigree QR:   {row[11]}")

    # Verify notes column is clean (NULL for user entry)
    cur.execute("SELECT COUNT(*) FROM horses WHERE notes IS NOT NULL")
    notes_count = cur.fetchone()[0]
    print(f"\nNotes column: {notes_count} entries have data (should be 0 — reserved for user)")

    # Color distribution
    print(f"\nHorses by color:")
    for row in cur.execute(
            "SELECT color, COUNT(*) FROM horses GROUP BY color ORDER BY COUNT(*) DESC"):
        print(f"  {row[0]:25s} {row[1]:3d}")

    conn.close()
    doc.close()
    print(f"\nDatabase saved to: {DB_PATH}")
    print(f"Photos saved to:   {PHOTO_DIR}/")


if __name__ == "__main__":
    main()
