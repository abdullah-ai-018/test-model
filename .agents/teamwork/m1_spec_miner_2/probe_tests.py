import xml.etree.ElementTree as ET
import numpy as np
import cv2
import shapely.wkt
from shapely.geometry import Polygon, MultiPolygon
from PIL import Image

def test_cubicasa_svg():
    svg_data = """<svg viewBox="0 0 1000 800" xmlns="http://www.w3.org/2000/svg">
      <g id="Walls">
        <polygon class="Wall" points="100,100 200,100 200,120 100,120" />
        <polygon class="Wall" points="200,100 200,300 180,300 180,100" />
      </g>
    </svg>"""

    root = ET.fromstring(svg_data)
    viewbox = root.attrib.get('viewBox', '0 0 1000 800').split()
    vb_w, vb_h = float(viewbox[2]), float(viewbox[3])
    target_h, target_w = 800, 1000
    scale_x = target_w / vb_w
    scale_y = target_h / vb_h

    mask = np.zeros((target_h, target_w), dtype=np.uint8)

    for elem in root.iter():
        tag = elem.tag.split('}')[-1]
        cls = elem.attrib.get('class', '')
        if tag == 'polygon' and 'Wall' in cls:
            points_str = elem.attrib.get('points', '')
            pts = []
            for pair in points_str.strip().split():
                if ',' in pair:
                    x, y = map(float, pair.split(','))
                    pts.append([int(round(x * scale_x)), int(round(y * scale_y))])
            if pts:
                pts_arr = np.array(pts, dtype=np.int32)
                cv2.fillPoly(mask, [pts_arr], color=3)

    print("SVG Mask unique values:", np.unique(mask))
    print("SVG Wall pixel count:", np.sum(mask == 3))
    assert np.sum(mask == 3) > 0

def test_tiling_engine():
    # Large canvas e.g. 1728 x 2592
    H, W = 1728, 2592
    tile_size = 512
    overlap = 0.20
    stride = int(round(tile_size * (1 - overlap))) # 410
    print(f"Tile size: {tile_size}, Stride: {stride}")

    y_steps = []
    y = 0
    while y + tile_size <= H:
        y_steps.append(y)
        y += stride
    if y_steps[-1] + tile_size < H:
        y_steps.append(H - tile_size) # boundary tile to cover the edge

    x_steps = []
    x = 0
    while x + tile_size <= W:
        x_steps.append(x)
        x += stride
    if x_steps[-1] + tile_size < W:
        x_steps.append(W - tile_size)

    print(f"Tiling grid: {len(y_steps)} rows x {len(x_steps)} cols = {len(y_steps)*len(x_steps)} tiles")
    print(f"y_steps: {y_steps}")
    print(f"x_steps: {x_steps}")

    # Check coverage
    coverage = np.zeros((H, W), dtype=np.int32)
    for y0 in y_steps:
        for x0 in x_steps:
            coverage[y0:y0+tile_size, x0:x0+tile_size] += 1
    
    assert np.min(coverage) >= 1, "Coverage gap found!"
    print(f"Coverage verified! Min coverage: {np.min(coverage)}, Max coverage: {np.max(coverage)}")

if __name__ == '__main__':
    test_cubicasa_svg()
    test_tiling_engine()
    print("All probe tests passed successfully!")


def test_stitching():
    H, W = 1728, 2592
    tile_size = 512
    overlap = 0.20
    stride = int(round(tile_size * (1 - overlap)))

    # Create dummy ground truth full image
    gt_full = np.zeros((H, W), dtype=np.float32)
    gt_full[200:400, 300:1500] = 1.0 # Wall strip

    # Extract tiles
    y_steps = [0, 410, 820, 1216]
    x_steps = [0, 410, 820, 1230, 1640, 2050, 2080]

    tiles = []
    coords = []
    for y0 in y_steps:
        for x0 in x_steps:
            tile = gt_full[y0:y0+tile_size, x0:x0+tile_size]
            tiles.append(tile)
            coords.append((y0, x0))

    # Reconstruct with 2D Hann window weighting
    wx = np.hanning(tile_size)
    wy = np.hanning(tile_size)
    window_2d = np.outer(wy, wx).astype(np.float32)
    # Avoid zero boundary by adding eps
    window_2d = np.clip(window_2d, 1e-4, 1.0)

    recon_num = np.zeros((H, W), dtype=np.float32)
    recon_den = np.zeros((H, W), dtype=np.float32)

    for (y0, x0), tile in zip(coords, tiles):
        recon_num[y0:y0+tile_size, x0:x0+tile_size] += tile * window_2d
        recon_den[y0:y0+tile_size, x0:x0+tile_size] += window_2d

    reconstructed = recon_num / recon_den
    max_err = np.max(np.abs(reconstructed - gt_full))
    print(f"Reconstruction max error: {max_err}")
    assert max_err < 1e-5, f"Reconstruction error too high: {max_err}"
    print("Seamless stitching with 2D Hann apodization verified successfully!")

test_stitching()


def test_visual_qc():
    # Create synthetic RGB tile (512x512)
    img_tile = np.full((512, 512, 3), 245, dtype=np.uint8) # light gray background
    # draw some CAD lines
    cv2.line(img_tile, (50, 50), (450, 50), (0, 0, 0), 2)
    cv2.line(img_tile, (100, 100), (100, 400), (50, 50, 50), 3)

    # Create synthetic uint8 mask
    mask_tile = np.zeros((512, 512), dtype=np.uint8)
    mask_tile[45:55, 50:450] = 1 # Drywall (Green)
    mask_tile[95:405, 95:105] = 2 # Non-Drywall (Red)
    mask_tile[200:250, 200:300] = 3 # Uncertain (Yellow)

    # Palette
    color_map = {
        0: (0, 0, 0),        # Transparent / unused
        1: (0, 255, 0),      # Drywall: Green (BGR: 0, 255, 0)
        2: (0, 0, 255),      # Non-Drywall: Red (BGR: 0, 0, 255)
        3: (0, 255, 255)     # Uncertain: Yellow (BGR: 0, 255, 255)
    }

    # Translucent overlay
    alpha = 0.45
    overlay = img_tile.copy()
    for cls_id, bgr_color in color_map.items():
        if cls_id == 0:
            continue
        cls_mask = (mask_tile == cls_id)
        if np.any(cls_mask):
            colored_layer = np.zeros_like(img_tile)
            colored_layer[cls_mask] = bgr_color
            # Blending: pixel = alpha * color + (1 - alpha) * orig
            overlay[cls_mask] = cv2.addWeighted(img_tile, 1 - alpha, colored_layer, alpha, 0)[cls_mask]

    # Triplet construction
    # 1. Original RGB
    # 2. Mask visualization (colored mask on white background)
    vis_mask = np.full((512, 512, 3), 255, dtype=np.uint8)
    for cls_id, bgr_color in color_map.items():
        if cls_id == 0:
            continue
        vis_mask[mask_tile == cls_id] = bgr_color

    # 3. Overlay
    triplet = np.hstack([img_tile, vis_mask, overlay])
    assert triplet.shape == (512, 1536, 3)
    print("Visual QC triplet constructed successfully! Shape:", triplet.shape)

test_visual_qc()


def test_tile_filtering():
    patch_size = 512
    # 1. Corrupted tile: None or wrong shape
    # 2. Corrupted tile: invalid mask values
    invalid_mask = np.full((512, 512), 4, dtype=np.uint8)
    valid_mask = np.zeros((512, 512), dtype=np.uint8)
    valid_mask[50:60, 50:60] = 1 # wall

    # 3. Completely blank image
    blank_img = np.full((512, 512, 3), 255, dtype=np.uint8)
    # 4. Linework without wall (hard negative)
    hard_neg_img = np.full((512, 512, 3), 255, dtype=np.uint8)
    cv2.putText(hard_neg_img, "ELEVATOR", (100, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

    def evaluate_tile(img, mask, keep_blank_prob=0.0):
        # Integrity checks
        if img is None or mask is None:
            return False, "CORRUPTED_NULL"
        if img.shape != (patch_size, patch_size, 3):
            return False, "CORRUPTED_SHAPE"
        if mask.shape != (patch_size, patch_size):
            return False, "CORRUPTED_MASK_SHAPE"
        if np.any(mask > 3):
            return False, "CORRUPTED_MASK_VALUES"
        
        has_walls = np.any(mask > 0)
        img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img_std = np.std(img_gray)
        is_pure_blank = (img_std < 2.0) and (np.mean(img_gray) > 250)

        if is_pure_blank and not has_walls:
            return False, "EMPTY_PURE_BLANK"

        if not has_walls and not is_pure_blank:
            # Hard negative: contains drawing linework/text but no walls
            return True, "VALID_HARD_NEGATIVE"

        return True, "VALID_WALL_SAMPLE"

    assert evaluate_tile(blank_img, valid_mask)[0] == True # has walls, keep even if blank background
    blank_mask = np.zeros((512, 512), dtype=np.uint8)
    assert evaluate_tile(blank_img, blank_mask)[0] == False # pure blank without walls -> filter!
    assert evaluate_tile(hard_neg_img, blank_mask)[0] == True # hard negative -> keep!
    assert evaluate_tile(hard_neg_img, invalid_mask)[0] == False # corrupted mask value > 3 -> reject!
    print("Tile filtering logic verified successfully!")

test_tile_filtering()
