import os
import sys
import json
import fitz  # PyMuPDF
import re

print("=== STARTING FOCUSED DRAWINGS INSPECTION ===")

target_pdfs = [
    r"C:\Users\TEC ZONE\Downloads\3.1-all-architectural-darwings.pdf",
    r"C:\Users\TEC ZONE\Downloads\Bid Set.pdf",
    r"C:\Users\TEC ZONE\Downloads\all_wall_partition_types.pdf",
    r"C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf",
    r"C:\Users\TEC ZONE\Downloads\Drywall_QTO_SOP.pdf",
    r"C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages (1).pdf",
    r"C:\Users\TEC ZONE\Downloads\drywall_relevant_full_pages.pdf",
    r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf",
    r"C:\Users\TEC ZONE\Downloads\floor_wise_new_wall_partition_tags.pdf",
    r"C:\Users\TEC ZONE\Downloads\PROTake-QTO-ABDULLAH-USMAN.pdf",
    r"C:\Users\TEC ZONE\Downloads\protake_ai_wall_partition_data.pdf",
    r"C:\Users\TEC ZONE\Downloads\QTO-Protake.pdf",
    r"C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf",
    r"C:\Users\TEC ZONE\Downloads\wall_partition_data_json.pdf",
    r"C:\Users\TEC ZONE\OneDrive\Documents\2026-09-10 Spark Lake Grove - Permit Set.pdf",
    r"C:\Users\TEC ZONE\OneDrive\Documents\drywall_walls_marked_red_by_Usman.pdf",
    r"C:\Users\TEC ZONE\OneDrive\Desktop\image-canvas-project\sample_drawings\commercial_plan_with_finish_schedule.pdf",
    r"C:\Users\TEC ZONE\OneDrive\Desktop\image-canvas-project\sample_drawings\synthetic_office_plan.pdf"
]

results = {}

for p in target_pdfs:
    if not os.path.exists(p):
        print(f"File NOT found: {p}")
        continue
    
    file_size = os.path.getsize(p)
    print(f"\nAnalyzing: {p} ({round(file_size/(1024*1024), 2)} MB)")
    
    try:
        doc = fitz.open(p)
        num_pages = len(doc)
        
        pdf_info = {
            "path": p,
            "filename": os.path.basename(p),
            "size_bytes": file_size,
            "size_mb": round(file_size / (1024 * 1024), 2),
            "page_count": num_pages,
            "sheets_found": {},
            "key_text_matches": {},
            "pages_detail": []
        }
        
        # We want to specifically search for sheets: A-101, A-102, A-103, A-104, A-900, A-901, A-902, A-910
        # and keywords: "99th", "MTA", "PARTITION", "DRYWALL", "WALL TYPE", "GYPSUM", "C-48526"
        target_keys = ["A-101", "A-102", "A-103", "A-104", "A-900", "A-901", "A-902", "A-910", "99TH", "MTA", "C-48526", "PARTITION", "DRYWALL", "GYPSUM BOARD", "FIRE RATED"]
        
        for k in target_keys:
            pdf_info["key_text_matches"][k] = []
            
        for page_idx in range(num_pages):
            page = doc[page_idx]
            rect = [page.rect.width, page.rect.height]
            rot = page.rotation
            text = page.get_text("text")
            upper_text = text.upper()
            
            # Check drawings/vector count
            drawings = page.get_drawings()
            num_drawings = len(drawings)
            images = page.get_images()
            num_images = len(images)
            
            # Detect sheet number from text
            # Often near bottom right or sheet title box
            sheet_matches = re.findall(r'\b([A-Z]{1,2}-?\d{3}(\.\d{1,2})?)\b', upper_text)
            sheet_numbers = list(set([m[0] for m in sheet_matches if m[0].startswith("A-") or m[0].startswith("G-") or m[0].startswith("CS")]))
            
            for k in target_keys:
                if k in upper_text:
                    pdf_info["key_text_matches"][k].append(page_idx + 1)
            
            # Extract sample lines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            relevant_lines = [l for l in lines if any(k in l.upper() for k in ["A-10", "A-90", "99TH", "PARTITION", "DRYWALL", "MTA", "SCHEDULE", "FLOOR PLAN"])]
            
            pdf_info["pages_detail"].append({
                "page_num": page_idx + 1,
                "dimensions": rect,
                "rotation": rot,
                "num_vector_drawings": num_drawings,
                "num_images": num_images,
                "is_vector": num_drawings > 50,
                "sheet_codes": sheet_numbers[:5],
                "sample_relevant_lines": relevant_lines[:5]
            })
            
        # Clean up empty matches
        pdf_info["key_text_matches"] = {k: v for k, v in pdf_info["key_text_matches"].items() if len(v) > 0}
        
        results[p] = pdf_info
        doc.close()
        print(f"Finished {os.path.basename(p)}: {num_pages} pages, matches: {list(pdf_info['key_text_matches'].keys())}")
        
    except Exception as e:
        print(f"Error processing {p}: {e}")
        results[p] = {"path": p, "error": str(e)}

out_file = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_1\focused_drawings_audit.json"
with open(out_file, "w") as f:
    json.dump(results, f, indent=2)

print(f"\nFocused inspection saved to {out_file}")
