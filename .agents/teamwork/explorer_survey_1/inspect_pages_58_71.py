import fitz

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

for i in range(58, len(doc)):
    page = doc[i]
    text = page.get_text("text")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    print(f"\n================ PAGE {i+1} (index {i}) ================")
    # Look for Sheet Name / Title
    for idx, l in enumerate(lines):
        if any(term in l for term in ['A-900', 'A-901', 'A-902', 'A-805', 'PARTITION', 'PARTITION TYPES']):
            print(f"Line {idx}: {l}")
    print("--- First 5 lines ---")
    print(lines[:5])
    print("--- Last 10 lines ---")
    print(lines[-10:])

doc.close()
