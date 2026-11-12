import fitz
import re
import json

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

sheet_map = []

for page_idx in range(len(doc)):
    page = doc[page_idx]
    text = page.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # MTA Title block usually has drawing number in a box or near the bottom/right
    # Let's search lines from bottom up
    dwg_candidates = []
    title_candidates = []
    
    # Common sheet patterns
    for l in lines:
        if re.match(r'^(T-001|CS\d+(\.\d+)?|G-\d{3}|LS-\d{3}|A-\d{3}|AV-\d{3}|FA-\d{3}|EN-\d{3}|FO-\d{3}|SS-\d{3})$', l):
            dwg_candidates.append(l)

    # Let's inspect text blocks near the title block area
    # Note: page.rect is (0, 0, 2592, 1728) with rotation 90.
    # In rotated coordinates, bottom right of the title block
    blocks = page.get_text("blocks")
    
    sheet_map.append({
        "page_index": page_idx,
        "page_num": page_idx + 1,
        "detected_dwg": dwg_candidates,
        "line_count": len(lines),
        "drawings_count": len(page.get_drawings()),
        "first_lines": lines[:3],
        "last_lines": lines[-10:] if len(lines) >= 10 else lines
    })

doc.close()

with open(r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\sheets_detected.json", "w") as f:
    json.dump(sheet_map, f, indent=2)

print("Sheet detection complete. Sample of first 15 pages:")
for s in sheet_map[:15]:
    print(f"Page {s['page_num']:2d} (idx {s['page_index']:2d}): dwg={s['detected_dwg']} | last={s['last_lines'][-3:]}")
