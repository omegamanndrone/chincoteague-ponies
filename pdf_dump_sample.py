# pdf_dump_sample.py
import pdfplumber
from pathlib import Path

PDF_PATH = r"C:\Users\Workstation\Desktop\23cc6d_08d053fa21d8458eb748d7183afb17a4.pdf"

with pdfplumber.open(PDF_PATH) as pdf:
    print(f"Total pages: {len(pdf.pages)}\n")
    
    for i in range(min(3, len(pdf.pages))):          # first 3 pages only
        page = pdf.pages[i]
        print(f"{'='*60}")
        print(f"PAGE {i+1}")
        print(f"{'='*60}")
        
        text = page.extract_text() or "(no text extracted)"
        print("RAW TEXT:")
        print(text[:2000])                        # first 2000 chars so it's not too long
        print("\nTABLES FOUND:")
        
        tables = page.extract_tables()
        if tables:
            for idx, table in enumerate(tables):
                print(f"  Table {idx+1} ({len(table)} rows):")
                for row in table[:10]:            # first 10 rows of each table
                    print("   ", row)
        else:
            print("  (no tables on this page)")
        
        print("\n")
