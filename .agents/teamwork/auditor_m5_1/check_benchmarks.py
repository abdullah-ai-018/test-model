import sys
from pathlib import Path
sys.path.insert(0, str(Path(".").resolve()))
import fitz
from drywall_detection.tests.test_classification import BENCHMARK_REGIONS

pdf_path = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
doc = fitz.open(pdf_path)

print(f"Total benchmark regions: {len(BENCHMARK_REGIONS)}")
for r in BENCHMARK_REGIONS:
    pno = r["page_idx"]
    page = doc[pno]
    rect = fitz.Rect(*r["pdf_bbox"])
    text_in_rect = page.get_text("text", clip=rect).strip().replace("\n", " ")
    drawings = page.get_drawings()
    intersecting_paths = sum(1 for d in drawings if rect.intersects(d["rect"]))
    print(f"Region {r['id']} ({r['sheet']}, Page {pno}): bbox={r['pdf_bbox']}, expected={r['expected_class']}")
    print(f"   description: {r['description']}")
    print(f"   tags: {r['tags']}")
    print(f"   clip text ({len(text_in_rect)} chars): {text_in_rect[:100]}")
    print(f"   intersecting CAD paths: {intersecting_paths}")
