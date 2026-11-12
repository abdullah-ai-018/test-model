import fitz

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)
page = doc[14]

# Look for drawings within 20 points of (767.1, 1096.7)
tx, ty = 767.1, 1096.7
drawings = page.get_drawings()
near_drawings = []
for d in drawings:
    rect = d["rect"]
    if abs(rect.x0 - tx) < 30 and abs(rect.y0 - ty) < 30:
        near_drawings.append(d)

print(f"Found {len(near_drawings)} drawing elements near tag '5E' at ({tx}, {ty}):")
for d in near_drawings[:5]:
    print(f"  type={d.get('type')}, rect={d.get('rect')}, items_count={len(d.get('items', []))}")
    for it in d.get("items", [])[:5]:
        print(f"     item: {it}")

doc.close()
