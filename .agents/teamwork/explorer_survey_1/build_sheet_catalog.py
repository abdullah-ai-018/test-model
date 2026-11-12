import fitz
import re
import json

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

# Let's read sheet index on page 2 (0-indexed)
index_page = doc[2]
index_text = index_page.get_text("text")
index_lines = [l.strip() for l in index_text.splitlines() if l.strip()]

# Let's build a map from sheet number to title from page 3 index
known_sheets = {}
for i in range(len(index_lines)-1):
    l = index_lines[i]
    if re.match(r'^[A-Z]{1,3}-\d{3}(\.\d+)?$', l):
        title = index_lines[i+1]
        known_sheets[l] = title

print(f"Parsed {len(known_sheets)} sheets from Master Sheet List:")
for k, v in list(known_sheets.items())[:10]:
    print(f"  {k}: {v}")

# Now for each page in doc, find which sheet it actually is
catalog = []
for p_idx in range(len(doc)):
    page = doc[p_idx]
    text = page.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    
    # MTA title block has sheet number in lower right
    # Rect is (0, 0, 2592, 1728), rot 90
    # Let's find blocks in the title block area or match known sheet codes
    matched_dwg = None
    matched_title = None
    
    # Look for known sheets appearing in the page lines
    # Usually in the title block, the drawing number appears alone
    # Check bottom lines of the page
    for l in reversed(lines[-40:] if len(lines) >= 40 else lines):
        if l in known_sheets:
            matched_dwg = l
            matched_title = known_sheets[l]
            break
        elif re.match(r'^(T-001|G-\d{3}|LS-\d{3}|A-\d{3}|AV-\d{3}|FA-\d{3})$', l):
            matched_dwg = l
            matched_title = known_sheets.get(l, "Custom Title")
            break

    # If still not found, check all lines
    if not matched_dwg:
        # Check first page
        if p_idx == 0:
            matched_dwg = "COVER / TITLE"
            matched_title = "ARCHITECTURAL INTERIOR SET - COVER"
        elif p_idx == 1:
            matched_dwg = "G-001"
            matched_title = "MASTER LEGENDS"
        elif p_idx == 2:
            matched_dwg = "G-002"
            matched_title = "MASTER SHEET LIST"
        else:
            for l in reversed(lines):
                if re.match(r'^[A-Z]{1,3}-\d{3}$', l):
                    matched_dwg = l
                    matched_title = known_sheets.get(l, "Unknown")
                    break

    catalog.append({
        "page_index": p_idx,
        "page_num": p_idx + 1,
        "sheet_num": matched_dwg,
        "sheet_title": matched_title,
        "drawings_count": len(page.get_drawings()),
        "text_chars": len(text)
    })

doc.close()

with open(r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\sheet_catalog.json", "w") as f:
    json.dump(catalog, f, indent=2)

print("\nFull 71-Page Sheet Catalog:")
for c in catalog:
    print(f"Page {c['page_num']:2d} (idx {c['page_index']:2d}): {c['sheet_num']:<8} | {str(c['sheet_title'])[:45]:<45} | Vectors: {c['drawings_count']:5d} | TextChars: {c['text_chars']:5d}")
