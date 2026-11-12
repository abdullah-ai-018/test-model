import fitz

p27 = r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf'
p71 = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'

doc27 = fitz.open(p27)
doc71 = fitz.open(p71)

print(f"Comparing {p27} (27 pages) to {p71} (71 pages)...")

# Map 27 pages to 71 pages by matching text hashes or first 100 characters
mapping = {}
for i in range(len(doc27)):
    t27 = doc27[i].get_text("text").strip()[:300]
    matched_j = None
    for j in range(len(doc71)):
        t71 = doc71[j].get_text("text").strip()[:300]
        if t27 == t71:
            matched_j = j
            break
    mapping[i] = matched_j

for i, j in mapping.items():
    print(f"27-page Doc Page {i+1} -> 71-page Doc Page {j+1 if j is not None else 'Unmatched'} (idx {j})")

doc27.close()
doc71.close()
