"""
Script to generate visual verification sample overlays for benchmark plan regions.
Saves high-res PNG and vector PDF overlays into drywall_detection/reports/sample_overlays/.
"""

import os
from pathlib import Path
import fitz
from PIL import Image

from drywall_detection.classification import DrywallClassifier
from drywall_detection.config import DEFAULT_MASTER_PDF_PATH
from drywall_detection.pipeline import WallAnnotator, VisualOverlayConfig
from drywall_detection.utils.coords import AffineTransformManager
from drywall_detection.vector.extractor import VectorExtractor
from drywall_detection.vector.schedule_parser import PartitionScheduleParser


def generate_overlays() -> None:
    pdf_path = Path(DEFAULT_MASTER_PDF_PATH)
    if not pdf_path.exists():
        pdf_path = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
    
    assert pdf_path.exists(), f"Master PDF not found at {pdf_path}"

    out_dir = Path("drywall_detection/reports/sample_overlays")
    out_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(pdf_path)
    extractor = VectorExtractor(dpi=150)
    schedule_parser = PartitionScheduleParser()
    classifier = DrywallClassifier(dpi=150)
    annotator = WallAnnotator(VisualOverlayConfig(dpi=150))
    atm = AffineTransformManager(dpi=150)

    # Benchmark regions to render
    regions = [
        {
            "id": "R01",
            "page_idx": 13,
            "sheet": "A-100",
            "pdf_bbox": (450.0, 900.0, 820.0, 1100.0),
            "title": "R01_A100_Cellar_Stair_D050_Drywall_5E",
        },
        {
            "id": "R02",
            "page_idx": 14,
            "sheet": "A-101",
            "pdf_bbox": (650.0, 880.0, 780.0, 1000.0),
            "title": "R02_A101_FirstFloor_Vestibule_Glass_GL2",
        },
        {
            "id": "R03",
            "page_idx": 14,
            "sheet": "A-101",
            "pdf_bbox": (700.0, 980.0, 820.0, 1120.0),
            "title": "R03_A101_FirstFloor_TV_Niche_09_Pier_11",
        },
        {
            "id": "R09",
            "page_idx": 62,
            "sheet": "A-900",
            "pdf_bbox": (350.0, 2200.0, 480.0, 2350.0),
            "title": "R09_A900_Detail_1A_CMU_Safety_Veto",
        },
    ]

    classified_pages = {}
    summary_by_page = {}

    pages_to_process = sorted(list({r["page_idx"] for r in regions}))

    for p_idx in pages_to_process:
        print(f"Processing Page {p_idx}...")
        page = doc[p_idx]
        sheet_name = f"A-{p_idx}"
        for r in regions:
            if r["page_idx"] == p_idx:
                sheet_name = r["sheet"]
                break

        walls = extractor.extract_wall_candidates(page)
        tags = schedule_parser.discover_tags(page, page_idx=p_idx, sheet_name=sheet_name)
        classified = classifier.classify_walls(walls=walls, tags=tags, page_idx=p_idx, sheet=sheet_name)
        summary = annotator._fallback_summary(classified)

        classified_pages[p_idx] = classified
        summary_by_page[p_idx] = summary

        # 1. Render full sheet raster image with overlay
        full_raster = annotator.render_raster_image(page, classified, summary)
        full_png_path = out_dir / f"sheet_{sheet_name}_p{p_idx}_overlay.png"
        full_raster.save(full_png_path, "PNG", optimize=True)
        print(f"Saved full raster: {full_png_path}")

        # 2. Render regional crops for regions on this page
        for r in regions:
            if r["page_idx"] == p_idx:
                x1, y1, x2, y2 = r["pdf_bbox"]
                px1, py1 = atm.pdf_to_pixel(x1, y2)
                px2, py2 = atm.pdf_to_pixel(x2, y1)

                min_px = max(0, int(min(px1, px2)) - 80)
                min_py = max(0, int(min(py1, py2)) - 80)
                max_px = min(full_raster.width, int(max(px1, px2)) + 80)
                max_py = min(full_raster.height, int(max(py1, py2)) + 80)

                crop = full_raster.crop((min_px, min_py, max_px, max_py))
                crop_path = out_dir / f"region_{r['id']}_{r['title']}_crop.png"
                crop.save(crop_path, "PNG")
                print(f"Saved region crop: {crop_path}")

    # 3. Generate annotated multi-page vector PDF
    annotated_pdf_path = out_dir / "M5_annotated_sample_drawings.pdf"
    annotator.generate_annotated_vector_pdf(
        src_pdf_path=pdf_path,
        classified_pages=classified_pages,
        output_pdf_path=annotated_pdf_path,
        summary_by_page=summary_by_page,
    )
    print(f"Saved annotated vector PDF: {annotated_pdf_path}")
    doc.close()


if __name__ == "__main__":
    generate_overlays()
