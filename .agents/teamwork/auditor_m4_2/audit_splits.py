import json
import os
import sys
from pathlib import Path

print("=== CHECK 3: ZERO DATA LEAKAGE & CAD TILE QUARANTINE ===")

split_dirs = [
    r"drywall_detection/data/processed/splits",
    r"drywall_detection/data/splits"
]

all_clean = True

for sdir in split_dirs:
    print(f"\n=======================================================")
    print(f"AUDITING SPLIT DIRECTORY: {sdir}")
    print(f"=======================================================")
    
    if not os.path.exists(sdir):
        print(f"Directory {sdir} does not exist!")
        continue
        
    split_files = {}
    for name in ["train", "val", "test", "quarantine"]:
        fpath = os.path.join(sdir, f"{name}.json")
        if os.path.exists(fpath):
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            split_files[name] = data
            print(f"Loaded {name}.json: type={type(data)}, length={len(data) if isinstance(data, (list, dict)) else 'N/A'}")
        else:
            print(f"File {fpath} not found!")

    # Check summary if exists
    sum_path = os.path.join(sdir, "splits_summary.json")
    if os.path.exists(sum_path):
        with open(sum_path, "r", encoding="utf-8") as f:
            summary = json.load(f)
        print(f"\nSummary in {sdir}: {json.dumps(summary, indent=2)}")

    # Extract items per split
    items_per_split = {}
    for name, data in split_files.items():
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if "samples" in data:
                items = data["samples"]
            elif "tiles" in data:
                items = data["tiles"]
            else:
                items = [data]
        else:
            items = []
        items_per_split[name] = items

    # Collect identifiers per split
    projects_by_split = {}
    drawings_by_split = {}
    images_by_split = {}
    masks_by_split = {}
    cad_records_by_split = {}

    for name, items in items_per_split.items():
        projects = set()
        drawings = set()
        images = set()
        masks = set()
        cad_records = []

        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            
            p = (item.get("project") or item.get("project_id") or 
                 item.get("site_id") or item.get("building_id") or "")
            d = (item.get("drawing") or item.get("drawing_id") or 
                 item.get("sheet") or item.get("sheet_id") or "")
            img = (item.get("image") or item.get("image_path") or 
                   item.get("tile_image") or item.get("image_file") or "")
            msk = (item.get("mask") or item.get("mask_path") or 
                   item.get("tile_mask") or item.get("mask_file") or "")
            
            # Normalize filenames for matching
            img_base = os.path.basename(img) if img else ""
            msk_base = os.path.basename(msk) if msk else ""
            
            if p: projects.add(str(p).strip())
            if d: drawings.add(str(d).strip())
            if img_base: images.add(img_base)
            if msk_base: masks.add(msk_base)

            # Identification of CAD / 99th Street / MTA tiles
            is_pseudo = item.get("is_pseudo_label", False) or item.get("pseudo_label", False) or item.get("weak_pseudo_label", False)
            source = str(item.get("source", "")).lower()
            dataset = str(item.get("dataset", "")).lower()
            str_repr = json.dumps(item).lower()

            is_cad = (
                is_pseudo or
                "99th" in str_repr or
                "mta" in str_repr or
                "c-48526" in str_repr or
                "a-10" in str_repr or
                "a-90" in str_repr or
                "cad" in source or
                "cad" in dataset
            )
            if is_cad:
                cad_records.append(item)

        projects_by_split[name] = projects
        drawings_by_split[name] = drawings
        images_by_split[name] = images
        masks_by_split[name] = masks
        cad_records_by_split[name] = cad_records

        print(f"\nSplit '{name}':")
        print(f"  Total items: {len(items)}")
        print(f"  Distinct projects ({len(projects)}): {sorted(list(projects))[:10]}")
        print(f"  Distinct drawings ({len(drawings)}): {sorted(list(drawings))[:10]}")
        print(f"  Distinct image files: {len(images)}")
        print(f"  Distinct mask files: {len(masks)}")
        print(f"  CAD / 99th St / Pseudo records: {len(cad_records)}")

    # Pairwise zero leakage check
    print("\n--- Pairwise Zero Data Leakage Checks ---")
    splits_to_compare = [n for n in ["train", "val", "test"] if n in items_per_split]
    
    for i in range(len(splits_to_compare)):
        for j in range(i + 1, len(splits_to_compare)):
            s1, s2 = splits_to_compare[i], splits_to_compare[j]
            p_leak = projects_by_split[s1].intersection(projects_by_split[s2])
            d_leak = drawings_by_split[s1].intersection(drawings_by_split[s2])
            img_leak = images_by_split[s1].intersection(images_by_split[s2])
            msk_leak = masks_by_split[s1].intersection(masks_by_split[s2])

            print(f"\nChecking pairwise separation between '{s1}' and '{s2}':")
            print(f"  Project intersection ({len(p_leak)}): {p_leak}")
            print(f"  Drawing intersection ({len(d_leak)}): {d_leak}")
            print(f"  Image file intersection ({len(img_leak)}): {img_leak}")
            print(f"  Mask file intersection ({len(msk_leak)}): {msk_leak}")

            if len(p_leak) > 0 or len(d_leak) > 0 or len(img_leak) > 0 or len(msk_leak) > 0:
                print(f"  >>> INTEGRITY VIOLATION: Leakage detected between {s1} and {s2}! <<<")
                all_clean = False
            else:
                print(f"  >>> PASS: Zero leakage between {s1} and {s2} confirmed.")

    # Quarantine verification
    print("\n--- CAD Tile Quarantine Verification ---")
    val_cad = cad_records_by_split.get("val", [])
    test_cad = cad_records_by_split.get("test", [])
    train_cad = cad_records_by_split.get("train", [])
    quar_cad = cad_records_by_split.get("quarantine", [])
    quar_items = items_per_split.get("quarantine", [])

    print(f"Quarantine total records: {len(quar_items)}")
    print(f"Quarantine CAD/99th St records: {len(quar_cad)}")
    print(f"Val CAD/99th St records: {len(val_cad)}")
    print(f"Test CAD/99th St records: {len(test_cad)}")
    print(f"Train CAD/99th St records: {len(train_cad)}")

    if len(val_cad) > 0:
        print(f"  >>> INTEGRITY VIOLATION: CAD tiles found in validation split ({len(val_cad)} items)! <<<")
        all_clean = False
    else:
        print("  >>> PASS: Zero CAD / 99th Street tiles in validation split.")

    if len(test_cad) > 0:
        print(f"  >>> INTEGRITY VIOLATION: CAD tiles found in test split ({len(test_cad)} items)! <<<")
        all_clean = False
    else:
        print("  >>> PASS: Zero CAD / 99th Street tiles in test split.")

print("\n" + "="*50)
if all_clean:
    print("CHECK 3 OVERALL RESULT: CLEAN - ZERO DATA LEAKAGE & STRICT CAD QUARANTINE CONFIRMED!")
else:
    print("CHECK 3 OVERALL RESULT: INTEGRITY VIOLATION DETECTED!")
print("="*50)
