import json
from pathlib import Path

def audit_split_dir(dir_path):
    print(f"\n==========================================")
    print(f"Auditing Split Directory: {dir_path}")
    print(f"==========================================")
    
    splits = {}
    for name in ['train', 'val', 'test', 'quarantine']:
        fpath = Path(dir_path) / f"{name}.json"
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                splits[name] = json.load(f)
            print(f"Loaded {name}.json: {len(splits[name]) if isinstance(splits[name], list) else type(splits[name])} items")
        else:
            print(f"Notice: {name}.json not found in {dir_path}")

    # Inspect structure of entries
    keys_per_split = {}
    for name, data in splits.items():
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            # Might be dict of lists or dict with samples
            if 'samples' in data:
                items = data['samples']
            elif 'tiles' in data:
                items = data['tiles']
            else:
                items = [data]
        else:
            items = []
        keys_per_split[name] = items
        print(f"Split '{name}' has {len(items)} sample records.")

    # Check project, drawing, image_path, mask_path sets
    project_sets = {}
    drawing_sets = {}
    image_sets = {}
    mask_sets = {}
    cad_tiles_per_split = {}

    for name, items in keys_per_split.items():
        projects = set()
        drawings = set()
        images = set()
        masks = set()
        cad_tiles = []

        for item in items:
            if isinstance(item, dict):
                p = item.get('project') or item.get('project_id') or item.get('site_id') or item.get('building_id')
                d = item.get('drawing') or item.get('drawing_id') or item.get('sheet')
                img = item.get('image') or item.get('image_path') or item.get('tile_image')
                msk = item.get('mask') or item.get('mask_path') or item.get('tile_mask')
                is_pseudo = item.get('is_pseudo_label', False) or item.get('pseudo_label', False)
                source = item.get('source', '')

                if p: projects.add(str(p))
                if d: drawings.add(str(d))
                if img: images.add(str(img))
                if msk: masks.add(str(msk))

                # Check if 99th Street or CAD
                is_cad = (
                    '99th' in str(p).lower() or '99th' in str(d).lower() or '99th' in str(img).lower() or
                    'cad' in str(source).lower() or is_pseudo or
                    'a-10' in str(d).lower() or 'a-9' in str(d).lower() or
                    'mta' in str(p).lower()
                )
                if is_cad:
                    cad_tiles.append(item)

        project_sets[name] = projects
        drawing_sets[name] = drawings
        image_sets[name] = images
        mask_sets[name] = masks
        cad_tiles_per_split[name] = cad_tiles

        print(f"Split '{name}':")
        print(f"  Projects ({len(projects)}): {projects}")
        print(f"  Drawings ({len(drawings)}): {drawings}")
        print(f"  Unique Images: {len(images)}")
        print(f"  Unique Masks: {len(masks)}")
        print(f"  CAD / 99th St / Pseudo tiles count: {len(cad_tiles)}")

    # Pairwise overlap checks
    split_names = [n for n in ['train', 'val', 'test'] if n in keys_per_split]
    leakage_found = False

    for i in range(len(split_names)):
        for j in range(i + 1, len(split_names)):
            s1, s2 = split_names[i], split_names[j]
            proj_overlap = project_sets[s1].intersection(project_sets[s2])
            draw_overlap = drawing_sets[s1].intersection(drawing_sets[s2])
            img_overlap = image_sets[s1].intersection(image_sets[s2])
            mask_overlap = mask_sets[s1].intersection(mask_sets[s2])

            print(f"\nOverlap check between '{s1}' and '{s2}':")
            print(f"  Project overlap ({len(proj_overlap)}): {proj_overlap}")
            print(f"  Drawing overlap ({len(draw_overlap)}): {draw_overlap}")
            print(f"  Image overlap ({len(img_overlap)}): {img_overlap}")
            print(f"  Mask overlap ({len(mask_overlap)}): {mask_overlap}")

            if proj_overlap or draw_overlap or img_overlap or mask_overlap:
                print(f"  >>> LEAKAGE DETECTED between {s1} and {s2}! <<<")
                leakage_found = True
            else:
                print(f"  >>> ZERO LEAKAGE verified between {s1} and {s2}. <<<")

    # Quarantine verification
    print("\n--- CAD Tile Quarantine Check ---")
    val_cad = cad_tiles_per_split.get('val', [])
    test_cad = cad_tiles_per_split.get('test', [])
    quar_items = keys_per_split.get('quarantine', [])

    print(f"CAD/Pseudo tiles in 'val': {len(val_cad)}")
    print(f"CAD/Pseudo tiles in 'test': {len(test_cad)}")
    print(f"Items in 'quarantine': {len(quar_items)}")

    if len(val_cad) > 0:
        print("  WARNING/FLAG: CAD / 99th Street tiles found in VAL split!")
        for c in val_cad[:5]:
            print("    Sample val CAD tile:", c)
    else:
        print("  VERIFIED: Zero CAD / 99th St tiles in val split.")

    return leakage_found, cad_tiles_per_split

print("Starting Split Audit...")
audit_split_dir(r"drywall_detection/data/processed/splits")
audit_split_dir(r"drywall_detection/data/splits")
