import fitz

candidates = [
    r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf'
]

for p in candidates:
    doc = fitz.open(p)
    print(f"\n=== {p} ({len(doc)} pages) ===")
    # Check page 0
    p0 = doc[0]
    txt0 = p0.get_text("text").splitlines()
    print(f"Page 0 rect={p0.rect}, rot={p0.rotation}, lines={len(txt0)}, drawings={len(p0.get_drawings())}")
    # Check annotations on pages
    annot_count = sum(len(list(doc[i].annots())) for i in range(len(doc)))
    print(f"Total annotations across document: {annot_count}")
    if annot_count > 0:
        for i in range(min(5, len(doc))):
            annots = list(doc[i].annots())
            if annots:
                print(f"  Page {i+1} has {len(annots)} annotations: {[a.type for a in annots[:5]]}")
    doc.close()
