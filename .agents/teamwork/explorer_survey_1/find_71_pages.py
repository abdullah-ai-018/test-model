import os, fitz

print("Starting scan for 71-page PDFs...")
count = 0
found = []
for root, dirs, files in os.walk(r'C:\Users\TEC ZONE'):
    dirs[:] = [d for d in dirs if d not in ['$Recycle.Bin', 'node_modules', '.git', '.cache', '.npm', 'AppData']]
    for f in files:
        if f.lower().endswith('.pdf'):
            p = os.path.join(root, f)
            count += 1
            try:
                doc = fitz.open(p)
                p_len = len(doc)
                if p_len == 71 or '48526' in f or '99th' in f.lower() or 'c-48526' in f.lower():
                    found.append((p, p_len, os.path.getsize(p)))
                    print(f"MATCH: {p} -> {p_len} pages, {os.path.getsize(p)} bytes")
                doc.close()
            except:
                pass

print(f"Scanned {count} PDFs. Total matches: {len(found)}")
for m in found:
    print(m)
