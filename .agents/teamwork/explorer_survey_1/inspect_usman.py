import fitz

p = r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf'
doc = fitz.open(p)
print(f"=== {p} ({len(doc)} pages) ===")
total_annots = 0
for i in range(len(doc)):
    page = doc[i]
    ann_list = []
    annot = page.first_annot
    while annot:
        ann_list.append((annot.type, annot.rect, annot.colors))
        annot = annot.next
    if ann_list:
        print(f"Page {i+1}: {len(ann_list)} annotations. Sample: {ann_list[:3]}")
    total_annots += len(ann_list)
print(f"Total annotations: {total_annots}")
doc.close()
