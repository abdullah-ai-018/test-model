import fitz
import json

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

print(f"File: {pdf_path}")
print(f"Total pages: {len(doc)}")

# Inspect first few pages
for i in range(min(5, len(doc))):
    p = doc[i]
    print(f"\n--- Page {i+1} ---")
    print(f"Rect: {p.rect}")
    print(f"Rotation: {p.rotation}")
    text = p.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    print(f"Line count: {len(lines)}")
    print(f"First 10 lines: {lines[:10]}")
    # check for key terms
    for term in ["99th", "C-48526", "PROGRESS SET", "95% CDs", "A-900", "A-901", "PARTITION"]:
        matches = [l for l in lines if term.lower() in l.lower()]
        if matches:
            print(f"  Match '{term}': {matches[:3]}")

doc.close()
