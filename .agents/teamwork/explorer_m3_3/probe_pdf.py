import fitz
import re

pdf_path = r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf"
doc = fitz.open(pdf_path)

print("--- Inspecting Page 62 (A-900) ---")
p62 = doc[62]
blocks62 = p62.get_text("blocks")
for b in blocks62:
    text = b[4].strip()
    if any(k in text.upper() for k in ["1A", "CMU", "PARTITION", "DETAIL"]):
        print(f"[{b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}]")
        print(text)
        print("-" * 40)

print("\n--- Inspecting Page 63 (A-901) ---")
p63 = doc[63]
blocks63 = p63.get_text("blocks")
for b in blocks63:
    text = b[4].strip()
    if any(k in text.upper() for k in ["GL1", "GL2", "09", "10", "11", "7A", "PARTITION", "DETAIL"]):
        print(f"[{b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f}]")
        print(text)
        print("-" * 40)
