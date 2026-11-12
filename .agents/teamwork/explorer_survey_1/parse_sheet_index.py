import fitz
import json

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

# Let's inspect page 3 (sheet index) in detail
p2 = doc[2] # 0-indexed page 2 is sheet 3
lines_p2 = [l.strip() for l in p2.get_text("text").splitlines() if l.strip()]

print("=== Page 3 lines containing sheet numbers or 'A-' or 'CS' or 'PARTITION' ===")
for idx, l in enumerate(lines_p2):
    if any(k in l for k in ['A-1', 'A-2', 'A-3', 'A-4', 'A-5', 'A-6', 'A-7', 'A-8', 'A-9', 'CS', 'G-', 'EN-']):
        print(f"Line {idx}: {l}")

doc.close()
