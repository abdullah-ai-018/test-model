import fitz

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)
p2 = doc[2]
lines = [l.strip() for l in p2.get_text("text").splitlines() if l.strip()]

for idx in range(60, 460):
    if idx < len(lines):
        print(f"{idx}: {lines[idx]}")

doc.close()
