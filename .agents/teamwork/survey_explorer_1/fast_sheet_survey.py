import os
import fitz
import json
import re

print("=== FAST SHEET SURVEY STARTING ===")

files_to_survey = {
    "Bid Set.pdf": r"C:\Users\TEC ZONE\Downloads\Bid Set.pdf",
    "file-1793194362940-560626729.pdf": r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf",
    "3.1-all-architectural-darwings.pdf": r"C:\Users\TEC ZONE\Downloads\3.1-all-architectural-darwings.pdf",
    "drywall_annotated_floor_plans.pdf": r"C:\Users\TEC ZONE\Downloads\drywall_annotated_floor_plans.pdf",
    "drywall_walls_marked_red_by_Usman.pdf": r"C:\Users\TEC ZONE\Downloads\drywall_walls_marked_red_by_Usman.pdf",
    "all_wall_partition_types.pdf": r"C:\Users\TEC ZONE\Downloads\all_wall_partition_types.pdf",
    "floor_wise_new_wall_partition_tags.pdf": r"C:\Users\TEC ZONE\Downloads\floor_wise_new_wall_partition_tags.pdf",
    "protake_ai_wall_partition_data.pdf": r"C:\Users\TEC ZONE\Downloads\protake_ai_wall_partition_data.pdf",
    "wall_partition_data_json.pdf": r"C:\Users\TEC ZONE\Downloads\wall_partition_data_json.pdf",
    "Drywall_QTO_SOP.pdf": r"C:\Users\TEC ZONE\Downloads\Drywall_QTO_SOP.pdf",
    "test Spark Lake Grove - Permit Set.pdf": r"C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf"
}

summary_output = {}

for name, fpath in files_to_survey.items():
    if not os.path.exists(fpath):
        continue
    
    doc = fitz.open(fpath)
    total_pages = len(doc)
    file_size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 2)
    
    pages_meta = []
    found_target_sheets = {}
    
    target_sheet_codes = [
        "A-101", "A-102", "A-103", "A-104",
        "A-900", "A-901", "A-902", "A-910",
        "CS-", "G-"
    ]
    
    for idx in range(total_pages):
        page = doc[idx]
        text = page.get_text("text")
        
        # Look for sheet number and title
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        
        # Search for sheet pattern like A-101 or A-900
        detected_sheets = []
        for l in lines:
            m = re.findall(r'\b(A-\d{3}(\.\d{1,2})?|CS\d+(\.\d+)?|G-\d{3})\b', l)
            for match in m:
                detected_sheets.append(match[0])
        detected_sheets = list(dict.fromkeys(detected_sheets))
        
        # Check title lines (lines containing FLOOR PLAN, PARTITION, WALL, SCHEDULE, ELEVATION, DETAIL, etc.)
        title_candidates = [l for l in lines if any(k in l.upper() for k in ["FLOOR PLAN", "PARTITION", "WALL TYPE", "SCHEDULE", "WALL DETAIL", "FIRESTOPPING", "LEGEND", "NOTES"])]
        
        # Check target codes
        for code in target_sheet_codes:
            if code in text.upper():
                if code not in found_target_sheets:
                    found_target_sheets[code] = []
                found_target_sheets[code].append(idx + 1)
        
        # Dimensions and vectors check (fast sample)
        rect = [page.rect.width, page.rect.height]
        
        pages_meta.append({
            "page": idx + 1,
            "dimensions": rect,
            "detected_sheets": detected_sheets,
            "title_candidates": title_candidates[:3],
            "text_length": len(text)
        })
        
    summary_output[name] = {
        "path": fpath,
        "size_mb": file_size_mb,
        "total_pages": total_pages,
        "target_sheet_matches": found_target_sheets,
        "first_page_dimensions": pages_meta[0]["dimensions"] if pages_meta else None,
        "pages": pages_meta
    }
    print(f"Done: {name} ({total_pages} pages) | Target matches: {list(found_target_sheets.keys())}")
    doc.close()

out_json = r"c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\survey_explorer_1\fast_survey_results.json"
with open(out_json, "w") as f:
    json.dump(summary_output, f, indent=2)

print(f"Results saved to {out_json}")
