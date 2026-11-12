import fitz
import re
from shapely.geometry import box, LineString, Polygon, Point

doc = fitz.open(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
page = doc[14] # A-101

# 1. Discover tags
tag_pattern = re.compile(r"^(1[A-E]|2[A-C]|3[A-D]|5[BDE]|7[A-CE-G]|8A|09|10|11|GL[12])$")
words = page.get_text("words")
tag_texts = [w for w in words if tag_pattern.match(w[4].strip())]

print(f"Found {len(tag_texts)} tag words.")

# 2. Extract drawings
drawings = page.get_drawings()
print(f"Found {len(drawings)} drawing primitives.")

# Look for leader lines connected to the first 5 tags
for tw in tag_texts[:5]:
    tag_name = tw[4].strip()
    # word bbox
    wb = box(tw[0] - 2, tw[1] - 2, tw[2] + 2, tw[3] + 2)
    # find lines near word
    connected_lines = []
    for d in drawings:
        for item in d.get("items", []):
            if item[0] == "l":
                p1, p2 = item[1], item[2]
                ls = LineString([(p1.x, p1.y), (p2.x, p2.y)])
                if ls.length > 3.0: # ignore zero-length or dots
                    # check if touches or close to word bbox
                    if wb.distance(ls) < 4.0:
                        connected_lines.append((ls, ls.length))
    print(f"Tag {tag_name} at ({tw[0]:.1f}, {tw[1]:.1f}): {len(connected_lines)} candidate connected line segments.")
    for cl, l_len in connected_lines[:3]:
        print(f"   Line: coords={list(cl.coords)}, length={l_len:.1f}")
