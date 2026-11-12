import fitz
import re

pdf_path = r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
doc = fitz.open(pdf_path)

page = doc[14] # Page 15, A-101
text = page.get_text("text")
lines = [l.strip() for l in text.splitlines() if l.strip()]

print(f"Sheet A-101 (Page 15) has {len(lines)} text lines")

# Let's search for partition tag patterns like '1A', '1B', '1C', '1D', '1E', '2B', '3A', '5B', '7A', '7F', etc.
tag_patterns = ['1A', '1B', '1C', '1D', '1E', '2B', '2C', '3A', '3D', '5B', '5D', '5E', '7A', '7B', '7C', '7E', '7F', '7G', '8A']
found_tags = {}
for l in lines:
    for t in tag_patterns:
        if l == t or l.startswith(t + " ") or l.endswith(" " + t):
            found_tags[t] = found_tags.get(t, 0) + 1

print("Found partition tag occurrences on A-101:")
for k, v in sorted(found_tags.items()):
    print(f"  Tag '{k}': {v} times")

# Let's also check for hexagon, oval, diamond, or circle symbols around tags
# By checking text block bounding boxes and surrounding vector shapes
blocks = page.get_text("blocks")
tag_blocks = [b for b in blocks if any(b[4].strip() == t for t in tag_patterns)]
print(f"\nSample of {len(tag_blocks)} exact tag blocks:")
for b in tag_blocks[:10]:
    print(f"  Tag: '{b[4].strip()}' at bbox ({b[0]:.1f}, {b[1]:.1f}, {b[2]:.1f}, {b[3]:.1f})")

doc.close()
