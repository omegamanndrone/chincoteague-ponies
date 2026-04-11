# test_pdf_type.py   (hardcoded for your PDF - no command line needed)
import fitz  # PyMuPDF

def is_scanned_pdf(pdf_path: str, text_threshold: float = 0.05) -> bool:
    doc = fitz.open(pdf_path)
    total_text_area = 0.0
    total_page_area = 0.0
    for page in doc:
        page_area = page.rect.width * page.rect.height
        total_page_area += page_area
        text_blocks = page.get_text("dict")["blocks"]
        text_area = sum(
            (b["bbox"][2] - b["bbox"][0]) * (b["bbox"][3] - b["bbox"][1])
            for b in text_blocks if b.get("type") == 0
        )
        total_text_area += text_area
    text_percentage = total_text_area / total_page_area if total_page_area > 0 else 0
    print(f"📊 Text coverage: {text_percentage:.1%}")
    return text_percentage < text_threshold

# Your exact PDF path (hardcoded)
pdf_path = r"C:\Users\Workstation\Desktop\23cc6d_08d053fa21d8458eb748d7183afb17a4.pdf"

print("Testing your PDF...")
if is_scanned_pdf(pdf_path):
    print("🚨 SCANNED PDF detected → we will use OCR")
else:
    print("✅ Searchable text PDF → direct extraction works")
