import os, fitz

def search_dir(base_dir, max_depth=4):
    print(f"Scanning {base_dir}...")
    for root, dirs, files in os.walk(base_dir):
        # limit depth
        rel = os.path.relpath(root, base_dir)
        depth = len(rel.split(os.sep))
        if depth > max_depth:
            dirs.clear()
            continue
        # skip git, node_modules, appdata
        dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', 'AppData', '$Recycle.Bin', 'Windows', 'Program Files', 'Program Files (x86)', '.npm', '.cache']]
        for f in files:
            fl = f.lower()
            if fl.endswith('.pdf'):
                if any(k in fl for k in ['99th', '48526', 'c-48526', 'c48526', 'progress', 'mta', 'architectural']):
                    p = os.path.join(root, f)
                    try:
                        sz = os.path.getsize(p)
                        doc = fitz.open(p)
                        pages = len(doc)
                        doc.close()
                        print(f"FOUND: {p} ({pages} pages, {sz} bytes)")
                    except Exception as e:
                        print(f"CANDIDATE: {p} (error: {e})")

search_dir(r'C:\Users\TEC ZONE\OneDrive')
search_dir(r'C:\Users\TEC ZONE\Downloads')
search_dir(r'C:\Users\TEC ZONE\Documents')
search_dir(r'E:')
print("Done searching.")
