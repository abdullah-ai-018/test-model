import os
import sys
import json
import re

print("=== STARTING ARCHITECTURAL DRAWINGS SCAN ===")

# Locations to scan
scan_dirs = [
    r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model",
    r"c:\Users\TEC ZONE\Downloads",
    r"c:\Users\TEC ZONE\OneDrive\Desktop",
    r"c:\Users\TEC ZONE\OneDrive\Documents"
]

explicit_candidates = [
    r'C:\Users\TEC ZONE\Downloads\3.1-all-architectural-darwings.pdf',
    r'C:\Users\TEC ZONE\Downloads\Bid Set.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages (1).pdf',
    r'C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf',
    r'C:\Users\TEC ZONE\OneDrive\Documents\drywall_walls_marked_red_by_Usman.pdf',
    r'C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf'
]

discovered_files = {}

# Check explicit candidates
for p in explicit_candidates:
    if os.path.exists(p):
        discovered_files[os.path.abspath(p)] = {
            "size_bytes": os.path.getsize(p),
            "size_mb": round(os.path.getsize(p) / (1024*1024), 2),
            "source": "explicit_candidate"
        }

# Scan workspace specifically
workspace_dir = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model"
for root, dirs, files in os.walk(workspace_dir):
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        if ext in ['.pdf', '.dwg', '.dxf', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.zip']:
            fp = os.path.abspath(os.path.join(root, f))
            discovered_files[fp] = {
                "size_bytes": os.path.getsize(fp),
                "size_mb": round(os.path.getsize(fp) / (1024*1024), 2),
                "source": "workspace"
            }

# Scan Downloads and Desktop for PDF files
for sdir in [r"c:\Users\TEC ZONE\Downloads", r"c:\Users\TEC ZONE\OneDrive\Desktop", r"c:\Users\TEC ZONE\OneDrive\Documents"]:
    if os.path.exists(sdir):
        try:
            for item in os.listdir(sdir):
                fp = os.path.join(sdir, item)
                if os.path.isfile(fp) and item.lower().endswith(".pdf"):
                    absp = os.path.abspath(fp)
                    if absp not in discovered_files:
                        discovered_files[absp] = {
                            "size_bytes": os.path.getsize(fp),
                            "size_mb": round(os.path.getsize(fp) / (1024*1024), 2),
                            "source": "user_dir"
                        }
        except Exception as e:
            print(f"Error reading {sdir}: {e}")

print(f"Total discovered candidate files: {len(discovered_files)}")

# Deep analysis of PDFs using fitz (PyMuPDF)
try:
    import fitz
except ImportError:
    print("fitz (PyMuPDF) not installed! Exiting deep inspection.")
    sys.exit(1)

pdf_reports = {}

for p, meta in discovered_files.items():
    if not p.lower().endswith(".pdf"):
        continue
    try:
        doc = fitz.open(p)
        page_count = len(doc)
        print(f"\nProcessing PDF: {p} (Pages: {page_count}, Size: {meta['size_mb']} MB)")
        
        target_sheets = {
            "A-101": [], "A-102": [], "A-103": [], "A-104": [],
            "A-900": [], "A-901": [], "A-902": [], "A-910": [],
            "CS": [], "G-": [], "PARTITION": [], "DRYWALL": [], "FIRE": []
        }
        
        pages_summary = []
        is_vector_based = False
        is_scanned = False
        total_vectors = 0
        total_images = 0
        
        for p_idx in range(page_count):
            page = doc[p_idx]
            text = page.get_text("text")
            drawings = page.get_drawings()
            images = page.get_images()
            
            num_drawings = len(drawings)
            num_images = len(images)
            total_vectors += num_drawings
            total_images += num_images
            
            # Check sheet patterns
            found_sheet_codes = []
            for target_key in target_sheets.keys():
                if target_key in text.upper():
                    target_sheets[target_key].append(p_idx)
                    found_sheet_codes.append(target_key)
            
            # Detect title block lines
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            sheet_title_candidates = [l for l in lines if any(k in l.upper() for k in ["FLOOR PLAN", "PARTITION", "WALL", "SCHEDULE", "DETAIL", "STREET", "MTA", "SUBWAY"])]
            
            pages_summary.append({
                "page_index": p_idx,
                "page_number": p_idx + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "rotation": page.rotation,
                "num_drawings": num_drawings,
                "num_images": num_images,
                "text_char_count": len(text),
                "matched_targets": found_sheet_codes,
                "sample_titles": sheet_title_candidates[:5]
            })

        is_vector = total_vectors > 100
        is_image_dominant = total_images > page_count and total_vectors < 50
        
        pdf_reports[p] = {
            "path": p,
            "size_mb": meta["size_mb"],
            "page_count": page_count,
            "is_vector": is_vector,
            "total_vectors": total_vectors,
            "total_images": total_images,
            "target_sheet_matches": {k: v for k, v in target_sheets.items() if len(v) > 0},
            "pages_summary": pages_summary
        }
        doc.close()
    except Exception as e:
        print(f"Error inspecting {p}: {e}")
        pdf_reports[p] = {"error": str(e), "path": p}

out_report_path = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_1\pdf_drawings_audit.json"
with open(out_report_path, "w") as f:
    json.dump({"discovered_files": discovered_files, "pdf_reports": pdf_reports}, f, indent=2)

print(f"\nPDF Drawings Audit written to {out_report_path}")
