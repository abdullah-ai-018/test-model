import fitz
import json
import re

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

print(f"Loaded {pdf_path}, pages={len(doc)}")

all_fonts = set()
pages_summary = []
rotation_set = set()
dimensions_set = set()

for page_idx in range(len(doc)):
    page = doc[page_idx]
    rect = (page.rect.width, page.rect.height)
    rot = page.rotation
    dimensions_set.add(rect)
    rotation_set.add(rot)

    # Drawings (vectors)
    drawings = page.get_drawings()
    num_drawings = len(drawings)
    num_rects = sum(1 for d in drawings if d.get("type") == "re" or ("rect" in d and len(d.get("items", [])) == 0))
    # Count drawing items
    path_items = sum(len(d.get("items", [])) for d in drawings)

    # Fonts
    fonts = page.get_fonts()
    for f in fonts:
        all_fonts.add(f[3]) # font name

    # Text
    text = page.get_text("text")
    blocks = page.get_text("blocks")
    lines = [l.strip() for l in text.splitlines() if l.strip()]

    # Try to identify Sheet Number & Title
    # Common sheet patterns: A-101, A-900, CS1.0, G-001, M-101, etc.
    sheet_num = None
    sheet_title = None
    
    # Look in the last blocks or lines for title block info
    # In MTA sets, title block often has drawing number
    # Let's search lines
    candidates = []
    for l in lines:
        if re.match(r'^(A-\d{3}(\.\d{2})?|CS\d+(\.\d+)?|EN-\d{3}|G-\d{3}|M-\d{3}|E-\d{3}|P-\d{3}|SP-\d{3}|FA-\d{3})$', l.strip()):
            candidates.append(l.strip())
        elif re.match(r'^[A-Z]{1,3}-\d{3}', l.strip()):
            candidates.append(l.strip())

    pages_summary.append({
        "page_index": page_idx,
        "page_number": page_idx + 1,
        "rect": [page.rect.width, page.rect.height],
        "rotation": rot,
        "vector_drawings_count": num_drawings,
        "path_items_count": path_items,
        "fonts_count": len(fonts),
        "text_blocks_count": len(blocks),
        "text_lines_count": len(lines),
        "candidate_sheet_numbers": candidates,
        "sample_lines": lines[:5]
    })

results = {
    "file_path": pdf_path,
    "total_pages": len(doc),
    "dimensions_set": [list(d) for d in dimensions_set],
    "rotation_set": list(rotation_set),
    "embedded_fonts_count": len(all_fonts),
    "embedded_fonts": sorted(list(all_fonts)),
    "pages": pages_summary
}

with open(r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\explorer_survey_1\pdf_deep_audit.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"Audit complete. Total pages: {len(doc)}")
print(f"Dimensions observed: {dimensions_set}")
print(f"Rotations observed: {rotation_set}")
print(f"Unique fonts count: {len(all_fonts)}")
doc.close()
