import fitz
import json

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

def inspect_partition_sheet(page_idx, sheet_name):
    page = doc[page_idx]
    blocks = page.get_text("blocks")
    # sort blocks by y0, then x0
    blocks_sorted = sorted(blocks, key=lambda b: (b[1], b[0]))
    print(f"\n=================== {sheet_name} (Page {page_idx+1}) ===================")
    print(f"Total blocks: {len(blocks)}")
    
    # Let's inspect text
    text = page.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # Find partition details headers
    for idx, l in enumerate(lines):
        if "PARTITION" in l.upper() or "RATED" in l.upper() or "GYPSUM" in l.upper() or "WALL" in l.upper() or "STUD" in l.upper():
            print(f"[{idx}] {l}")

inspect_partition_sheet(62, "A-900 PARTITION TYPES SHEET I")
inspect_partition_sheet(63, "A-901 PARTITION TYPES SHEET II")

doc.close()
