# pdf_dump_sample_fitz.py
import fitz  # PyMuPDF

PDF_PATH = r"C:\Users\Workstation\Desktop\23cc6d_08d053fa21d8458eb748d7183afb17a4.pdf"

doc = fitz.open(PDF_PATH)
print(f"Total pages: {len(doc)}\n")

for i in range(min(3, len(doc))):      # first 3 pages only
    page = doc[i]
    print(f"{'='*80}")
    print(f"PAGE {i+1} (raw text from PyMuPDF)")
    print(f"{'='*80}")
    
    text = page.get_text("text")       # this is what worked in the test
    print(text[:4000])                 # first ~4000 characters (plenty to see the layout)
    
    # Also show any tables/images if present
    tables = page.get_text("dict")["blocks"]
    table_count = sum(1 for b in tables if b.get("type") == 1)  # type 1 = image/table
    print(f"\n[Page has {table_count} image/table block(s)]\n")

doc.close()
print("✅ Done - copy the output above and paste it here")
