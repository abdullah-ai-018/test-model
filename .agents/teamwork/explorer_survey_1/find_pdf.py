import fitz
import os

candidates = [
    r'C:\Users\TEC ZONE\Downloads\3.1-all-architectural-darwings.pdf',
    r'C:\Users\TEC ZONE\Downloads\Bid Set.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages (1).pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf',
    r'C:\Users\TEC ZONE\OneDrive\Documents\drywall_walls_marked_red_by_Usman.pdf'
]

for p in candidates:
    if not os.path.exists(p):
        continue
    try:
        doc = fitz.open(p)
        print(f"=== {p} ({len(doc)} pages) ===")
        for i in range(len(doc)):
            txt = doc[i].get_text("text")
            for q in ["99th", "48526", "C-48526", "PROGRESS SET", "A-900", "A-901", "PARTITION SCHEDULE"]:
                if q.lower() in txt.lower():
                    print(f"  Page {i}: matches '{q}'")
                    for line in txt.splitlines():
                        if q.lower() in line.lower():
                            print(f"     {line.strip()[:100]}")
                    break
        doc.close()
    except Exception as e:
        print(f"Error reading {p}: {e}")
