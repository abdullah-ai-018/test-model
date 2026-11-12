import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

import fitz
from shapely.geometry import box

from drywall_detection.config import (
    DEFAULT_MASTER_PDF_PATH,
    USMAN_GROUND_TRUTH_PDF,
)
from drywall_detection.tests.test_classification import BENCHMARK_REGIONS

print("=== FORENSIC DIMENSION 2: BENCHMARK REGIONS & USMAN GT AUTHENTICITY ===")

# 1. Verify Usman Ground Truth PDF
print(f"Opening Usman PDF: {USMAN_GROUND_TRUTH_PDF}")
usman_doc = fitz.open(USMAN_GROUND_TRUTH_PDF)
print(f"Usman PDF page count: {len(usman_doc)}")

total_annots = 0
total_lines = 0
total_squares = 0
per_page_stats = []

for p_idx, page in enumerate(usman_doc):
    annots = list(page.annots() or [])
    lines = [a for a in annots if a.type[1] == "Line"]
    squares = [a for a in annots if a.type[1] == "Square"]
    total_annots += len(annots)
    total_lines += len(lines)
    total_squares += len(squares)
    per_page_stats.append((p_idx, len(annots), len(lines), len(squares)))

print(f"Total annots: {total_annots}, lines: {total_lines}, squares: {total_squares}")
for p_idx, t_a, l_a, s_a in per_page_stats:
    print(f"  Page {p_idx}: total={t_a}, lines={l_a}, squares={s_a}")

assert total_annots == 478, f"Expected 478 total annots, got {total_annots}"
assert total_lines == 239, f"Expected 239 line annots, got {total_lines}"
assert total_squares == 239, f"Expected 239 square annots, got {total_squares}"
print("-> Usman Ground Truth exactly matches 478 total annotations (239 lines + 239 squares)!")
usman_doc.close()

# 2. Verify Master PDF and text / tags in R01-R10 regions
print(f"\nOpening Master PDF: {DEFAULT_MASTER_PDF_PATH}")
master_doc = fitz.open(DEFAULT_MASTER_PDF_PATH)
print(f"Master PDF page count: {len(master_doc)}")

for r in BENCHMARK_REGIONS:
    rid = r["id"]
    p_idx = r["page_idx"]
    pdf_bbox = r["pdf_bbox"]
    expected_tags = r["tags"]
    
    page = master_doc[p_idx]
    rect = fitz.Rect(*pdf_bbox)
    region_text = page.get_text("text", clip=rect)
    
    # Check if expected tags appear in text or words in this bounding box
    words = page.get_text("words", clip=rect)
    found_words = [w[4] for w in words]
    
    print(f"\nRegion {rid} (Page {p_idx}, Sheet {r['sheet']}):")
    print(f"  BBox: {pdf_bbox}")
    print(f"  Expected tags: {expected_tags}")
    print(f"  Found words count in clip: {len(found_words)}")
    # Sample words
    print(f"  Sample words: {found_words[:10]}")
    for exp_t in expected_tags:
        # Check if exp_t is among the words
        matched = any(exp_t.upper() == w.upper() for w in found_words) or (exp_t in region_text)
        print(f"    Tag '{exp_t}' present in region text/words: {matched}")

master_doc.close()
print("\nDimension 2 verification complete.")
