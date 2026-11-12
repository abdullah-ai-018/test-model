import fitz
import re

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

print(f"Scanning 71 pages for sheet title blocks...")
results = []
for i in range(len(doc)):
    page = doc[i]
    text = page.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # In title block, sheet number is usually near the end of lines
    # Let's inspect the last 30 lines
    tail = lines[-30:] if len(lines) >= 30 else lines
    
    sheet_candidates = [l for l in tail if re.match(r'^(T-001|G-\d{3}|LS-\d{3}|A-\d{3}|AV-\d{3}|FA-\d{3})$', l)]
    # Also check title
    title = None
    for idx, l in enumerate(tail):
        if l in ["PARTITION TYPES SHEET I", "PARTITION TYPES SHEET II", "FIRST FLOOR CONSTRUCTION PLAN", "MASTER SHEET LIST"]:
            title = l
    
    if any("A-900" in l for l in tail) or any("A-901" in l for l in tail) or "PARTITION" in "".join(tail):
        print(f"Page {i+1} (idx {i}): candidates={sheet_candidates}, tail_sample={tail[-10:]}")
        results.append((i, sheet_candidates, tail))

doc.close()
