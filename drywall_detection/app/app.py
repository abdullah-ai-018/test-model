#!/usr/bin/env python3
"""
drywall_detection/app/app.py
===========================
Streamlit Interactive Local Testing Interface & Takeoff Analytics Dashboard
for Architectural Wall Detection and Drywall Classification.

Requirement R4 Compliance:
- Local PDF testing interface accepting vector-based and scanned PDFs / images.
- Multi-page document navigation and live progress indicators.
- Interactive side-by-side and tabbed visual inspection (Overlay, Side-by-Side, Raw Mask).
- Standard 4-class taxonomy:
    0: Background (White / Linework)
    1: Drywall (Green #00C853 / #00FF00)
    2: Non-Drywall (Red #D50000 / #FF0000)
    3: Uncertain (Yellow #FFD600 / #FFFF00)
- Takeoff statistics dashboard (wall area, class percentages, latency).
- Export capabilities: Download Annotated PDF (vector-preserving), PNG preview, JSON & CSV takeoff reports.
- Progress set disclosure notice (MTA 99th St 95% CDs calibration limitation).
"""

from __future__ import annotations

import csv
import io
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
from PIL import Image
import streamlit as st
import torch

# Ensure package root is in sys.path
APP_DIR = Path(__file__).resolve().parent
if APP_DIR.name == "app":
    PACKAGE_ROOT = APP_DIR.parent
    WORKSPACE_ROOT = PACKAGE_ROOT.parent
elif APP_DIR.name == "drywall_detection":
    PACKAGE_ROOT = APP_DIR
    WORKSPACE_ROOT = PACKAGE_ROOT.parent
else:
    PACKAGE_ROOT = APP_DIR
    WORKSPACE_ROOT = APP_DIR.parent

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

# PyMuPDF
try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

try:
    from drywall_detection.config import (
        BASE_DPI,
        DEFAULT_DPI,
        HIGH_RES_DPI,
        BEST_MODEL_DIR,
        CLASS_BACKGROUND,
        CLASS_DRYWALL,
        CLASS_NON_DRYWALL,
        CLASS_UNCERTAIN,
        NUM_CLASSES,
        CLASS_NAMES,
        CLASS_COLORS_HEX,
        CLASS_COLORS_RGB,
        DEFAULT_OVERLAY_ALPHA,
        DEFAULT_MASTER_PDF_PATH,
        REFERENCE_SET_NOTICE,
        TAG_1A_OVERRIDE_REASON,
    )
except ImportError:
    BASE_DPI = 72
    DEFAULT_DPI = 150
    HIGH_RES_DPI = 300
    BEST_MODEL_DIR = PACKAGE_ROOT / "checkpoints" / "best_model"
    CLASS_BACKGROUND = 0
    CLASS_DRYWALL = 1
    CLASS_NON_DRYWALL = 2
    CLASS_UNCERTAIN = 3
    NUM_CLASSES = 4
    CLASS_NAMES = {0: "Background", 1: "Drywall", 2: "Non-Drywall", 3: "Uncertain"}
    CLASS_COLORS_HEX = {
        "Background": "#FFFFFF",
        "Drywall": "#00C853",
        "Non-Drywall": "#D50000",
        "Uncertain": "#FFD600",
    }
    CLASS_COLORS_RGB = {
        0: (255, 255, 255),
        1: (0, 200, 83),
        2: (213, 0, 0),
        3: (255, 214, 0),
    }
    DEFAULT_OVERLAY_ALPHA = 0.45
    DEFAULT_MASTER_PDF_PATH = Path(r"C:\Users\TEC ZONE\Downloads\file-1793194362940-560626729.pdf")
    REFERENCE_SET_NOTICE = (
        "MTA Contract C-48526, 99th Street Phase 2 Interior Set (71 pages, 1728x2592 pt unrotated, "
        "90 deg CW rotation, 'PROGRESS SET 95% CDs 10/02/2026'). Notice: This reference PDF represents "
        "a 95% CDs progress set, not an approved final construction document. Pages represent a single "
        "project calibration sample and cannot prove cross-domain generalization."
    )
    TAG_1A_OVERRIDE_REASON = "Detail 1A on Sheet A-900 is explicitly 6\" FIRE RATED CMU (masonry / Non-Drywall)."

# Model loader import
try:
    from drywall_detection.pipeline.infer import StandaloneInferencer
except ImportError:
    try:
        from drywall_detection.checkpoints.best_model.infer import StandaloneInferencer
    except ImportError:
        StandaloneInferencer = None

try:
    from drywall_detection.pipeline.annotate import PDFAnnotator, mask_to_rgba_overlay
except ImportError:
    PDFAnnotator = None
    mask_to_rgba_overlay = None


# ==============================================================================
# 1. UI HELPER & STYLING FUNCTIONS
# ==============================================================================

def inject_custom_css() -> None:
    """Injects custom CSS styling for engineering cards, badges, and metrics."""
    st.markdown(
        """
        <style>
        .metric-card {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 12px 16px;
            border-left: 5px solid #1E88E5;
            box-shadow: 0 1px 3px rgba(0,0,0,0.08);
            margin-bottom: 10px;
        }
        .legend-container {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
            margin: 12px 0 16px 0;
            padding: 10px 14px;
            background-color: #f1f3f4;
            border-radius: 8px;
            border: 1px solid #e0e0e0;
        }
        .legend-chip {
            padding: 6px 14px;
            border-radius: 6px;
            font-size: 0.88rem;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            box-shadow: 0 1px 2px rgba(0,0,0,0.1);
        }
        .chip-drywall { background-color: #00C853; color: white; }
        .chip-nondrywall { background-color: #D50000; color: white; }
        .chip-uncertain { background-color: #FFD600; color: #212121; }
        .chip-bg { background-color: #FFFFFF; color: #424242; border: 1px solid #bdbdbd; }
        .disclosure-box {
            background-color: #fff8e1;
            border-left: 5px solid #ffa000;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 0.88rem;
            color: #5d4037;
            margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_color_legend() -> None:
    """Renders the standard 4-class semantic legend."""
    st.markdown(
        """
        <div class="legend-container">
            <span class="legend-chip chip-drywall">🟩 Drywall (GWB) — #00C853</span>
            <span class="legend-chip chip-nondrywall">🟥 Non-Drywall (CMU Veto / Glass / Conc) — #D50000</span>
            <span class="legend-chip chip-uncertain">🟨 Uncertain (Generic / Millwork) — #FFD600</span>
            <span class="legend-chip chip-bg">⬜ Background / Linework — #FFFFFF</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


@st.cache_resource(show_spinner="Loading SegFormer-B0 Champion Model...")
def load_cached_inferencer(checkpoint_dir: str, device: str) -> Optional[Any]:
    """Loads and caches the neural network inferencer in memory."""
    if StandaloneInferencer is None:
        st.error("StandaloneInferencer module could not be found.")
        return None
    try:
        inferencer = StandaloneInferencer(checkpoint_dir=checkpoint_dir, device=device)
        return inferencer
    except Exception as e:
        # Check fallback to standard BEST_MODEL_DIR if custom path failed
        fallback_dir = BEST_MODEL_DIR
        if str(Path(checkpoint_dir).resolve()) != str(fallback_dir.resolve()) and fallback_dir.exists():
            try:
                inferencer = StandaloneInferencer(checkpoint_dir=fallback_dir, device=device)
                return inferencer
            except Exception:
                pass
        st.error(f"Failed to load checkpoint from '{checkpoint_dir}': {e}")
        return None


# ==============================================================================
# 2. IMAGE & PDF PROCESSING HELPERS
# ==============================================================================

def render_pdf_page_to_image(doc: fitz.Document, page_idx: int, dpi: int = 150) -> Image.Image:
    """Renders a specific PDF page to an RGB PIL Image at given DPI."""
    page = doc.load_page(page_idx)
    zoom = dpi / float(BASE_DPI)
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def blend_overlay(
    image_rgb: np.ndarray,
    mask_uint8: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """
    Blends 4-class segmentation colors onto image in NumPy.
    Runs instantaneously (<50ms) to ensure slider adjustments are snappy.
    """
    overlay = image_rgb.copy().astype(np.float32)
    for class_idx, color in CLASS_COLORS_RGB.items():
        if class_idx == CLASS_BACKGROUND:
            continue
        match = (mask_uint8 == class_idx)
        if np.any(match):
            c_rgb = np.array(color, dtype=np.float32)
            overlay[match] = (1.0 - alpha) * overlay[match] + alpha * c_rgb
    return np.clip(overlay, 0, 255).astype(np.uint8)


def mask_to_rgb(mask_uint8: np.ndarray) -> np.ndarray:
    """Converts 2D class mask into solid RGB representation."""
    H, W = mask_uint8.shape
    rgb = np.full((H, W, 3), 255, dtype=np.uint8)
    for class_idx, color in CLASS_COLORS_RGB.items():
        if class_idx == CLASS_BACKGROUND:
            continue
        rgb[mask_uint8 == class_idx] = color
    return rgb


def compute_takeoff_stats(mask_uint8: np.ndarray, latency_sec: float = 0.0) -> Dict[str, Any]:
    """Computes comprehensive per-page takeoff statistics with zero-division safety."""
    total_pixels = int(mask_uint8.size)
    bg_pixels = int((mask_uint8 == CLASS_BACKGROUND).sum())
    drywall_pixels = int((mask_uint8 == CLASS_DRYWALL).sum())
    non_drywall_pixels = int((mask_uint8 == CLASS_NON_DRYWALL).sum())
    uncertain_pixels = int((mask_uint8 == CLASS_UNCERTAIN).sum())

    wall_total = drywall_pixels + non_drywall_pixels + uncertain_pixels

    wall_pct_canvas = (wall_total / total_pixels * 100.0) if total_pixels > 0 else 0.0
    drywall_pct_walls = (drywall_pixels / wall_total * 100.0) if wall_total > 0 else 0.0
    non_drywall_pct_walls = (non_drywall_pixels / wall_total * 100.0) if wall_total > 0 else 0.0
    uncertain_pct_walls = (uncertain_pixels / wall_total * 100.0) if wall_total > 0 else 0.0

    return {
        "total_pixels": total_pixels,
        "background_pixels": bg_pixels,
        "drywall_pixels": drywall_pixels,
        "non_drywall_pixels": non_drywall_pixels,
        "uncertain_pixels": uncertain_pixels,
        "wall_total_pixels": wall_total,
        "wall_pct_canvas": round(wall_pct_canvas, 2),
        "drywall_pct_walls": round(drywall_pct_walls, 2),
        "non_drywall_pct_walls": round(non_drywall_pct_walls, 2),
        "uncertain_pct_walls": round(uncertain_pct_walls, 2),
        "latency_sec": round(latency_sec, 3),
    }


def build_annotated_pdf_bytes(
    pdf_bytes: bytes,
    masks_dict: Dict[int, np.ndarray],
    dpi: int = 150,
    alpha: float = 0.45,
) -> bytes:
    """
    Constructs an annotated PDF using PyMuPDF, preserving native CAD geometry,
    MediaBox dimensions, and page rotation.
    """
    if fitz is None:
        raise ImportError("PyMuPDF is required to construct annotated PDFs.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    for page_idx, mask in masks_dict.items():
        if page_idx >= len(doc):
            continue
        page = doc.load_page(page_idx)

        # Generate RGBA transparent overlay
        H, W = mask.shape
        rgba = np.zeros((H, W, 4), dtype=np.uint8)
        alpha_byte = int(np.clip(alpha * 255.0, 0, 255))

        for c_idx, color in CLASS_COLORS_RGB.items():
            if c_idx == CLASS_BACKGROUND:
                continue
            match = (mask == c_idx)
            rgba[match, 0] = color[0]
            rgba[match, 1] = color[1]
            rgba[match, 2] = color[2]
            rgba[match, 3] = alpha_byte

        # Construct pixmap directly from bytes without lossy re-encoding
        pix_overlay = fitz.Pixmap(fitz.csRGB, W, H, rgba.tobytes(), True)

        # Insert overlay preserving native rotation and page dimensions
        page.insert_image(
            page.cropbox,
            pixmap=pix_overlay,
            rotate=page.rotation,
            overlay=True,
        )

    out_bytes = doc.tobytes(deflate=True, garbage=4)
    doc.close()
    return out_bytes


def build_takeoff_csv_str(pages_stats: List[Dict[str, Any]]) -> str:
    """Serializes takeoff statistics into tabular CSV string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "page_index",
        "sheet_name",
        "total_pixels",
        "wall_pixels",
        "wall_pct_canvas",
        "drywall_pixels",
        "drywall_pct_walls",
        "non_drywall_pixels",
        "non_drywall_pct_walls",
        "uncertain_pixels",
        "uncertain_pct_walls",
        "latency_sec",
    ])
    for item in pages_stats:
        writer.writerow([
            item.get("page_index", 1),
            item.get("sheet_name", f"Page {item.get('page_index', 1)}"),
            item.get("total_pixels", 0),
            item.get("wall_total_pixels", 0),
            item.get("wall_pct_canvas", 0.0),
            item.get("drywall_pixels", 0),
            item.get("drywall_pct_walls", 0.0),
            item.get("non_drywall_pixels", 0),
            item.get("non_drywall_pct_walls", 0.0),
            item.get("uncertain_pixels", 0),
            item.get("uncertain_pct_walls", 0.0),
            item.get("latency_sec", 0.0),
        ])
    return output.getvalue()


# ==============================================================================
# 3. MAIN STREAMLIT APPLICATION
# ==============================================================================

def main() -> None:
    st.set_page_config(
        page_title="Drywall Detection & Wall Classification Interface",
        page_icon="🏗️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_custom_css()

    # Session State Initialization
    if "cache" not in st.session_state:
        st.session_state["cache"] = {}
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = 0
    if "doc_bytes" not in st.session_state:
        st.session_state["doc_bytes"] = None
    if "doc_name" not in st.session_state:
        st.session_state["doc_name"] = "document"

    # Header & Capability Showcase
    st.title("🏗️ Drywall Detection & Wall Classification Interface")
    st.caption("Milestone M4: Local PDF Testing Interface & Takeoff Analytics Pipeline")

    # Badges row
    c_b1, c_b2, c_b3, c_b4 = st.columns(4)
    c_b1.info("**Model**: SegFormer-B0 Champion")
    c_b2.info("**Taxonomy**: 4-Class Semantic")
    c_b3.info("**Stitching**: 2D Hann Apodization")
    c_b4.info(f"**Execution Host**: {'CUDA GPU' if torch.cuda.is_available() else 'Windows Host CPU'}")

    # Mandatory 95% CDs Disclosure Notice
    st.markdown(
        f"""
        <div class="disclosure-box">
            <strong>⚠️ Progress Set Disclosure Notice:</strong> {REFERENCE_SET_NOTICE}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --------------------------------------------------------------------------
    # SIDEBAR: Configuration & Controls
    # --------------------------------------------------------------------------
    st.sidebar.header("⚙️ Configuration & Controls")

    checkpoint_dir = st.sidebar.text_input(
        "Checkpoint Directory",
        value=str(BEST_MODEL_DIR),
        help="Path containing best_model.pt and config.json",
    )

    available_devices = ["cpu"]
    if torch.cuda.is_available():
        available_devices.insert(0, "cuda")
    device = st.sidebar.selectbox("Inference Device", available_devices, index=0)

    # Reload model button
    if st.sidebar.button("🔄 Reload Model"):
        load_cached_inferencer.clear()
        st.sidebar.success("Model cache cleared!")

    inferencer = load_cached_inferencer(checkpoint_dir, device)
    if inferencer is not None:
        st.sidebar.success("✅ Model Ready: SegFormer-B0 (3.72M params)")
    else:
        st.sidebar.error("❌ Model not loaded. Check path.")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📐 Rendering & Tiling Settings")

    dpi = st.sidebar.select_slider(
        "Rendering Resolution (DPI)",
        options=[72, 100, 150, 200, 300],
        value=DEFAULT_DPI,
        help="72 DPI = Fast Preview; 150 DPI = Standard Quality; 300 DPI = High Resolution.",
    )

    alpha = st.sidebar.slider(
        "Overlay Transparency (Alpha)",
        min_value=0.10,
        max_value=0.90,
        value=DEFAULT_OVERLAY_ALPHA,
        step=0.05,
        help="Transparency of segmentation color mask over drawing.",
    )

    with st.sidebar.expander("🛠️ Advanced Tiling Controls"):
        tile_size = st.selectbox("Tile Size (px)", [256, 512, 1024], index=1)
        overlap = st.slider("Tile Overlap Fraction", min_value=0.0, max_value=0.50, value=0.20, step=0.05)
        st.caption("Hann window apodization ensures artifact-free tile blending.")

    # --------------------------------------------------------------------------
    # MAIN WORKSPACE: Input Selection
    # --------------------------------------------------------------------------
    st.subheader("1. Drawing Source Selection")
    source_mode = st.radio(
        "Choose Drawing Source",
        ["Upload File (PDF / Image)", "Load Sample Drawing from Workspace"],
        horizontal=True,
    )

    doc_stream: Optional[bytes] = None
    doc_type: str = "pdf"
    doc_filename: str = "document"

    if source_mode == "Upload File (PDF / Image)":
        uploaded_file = st.file_uploader(
            "Upload Architectural PDF or Image",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Upload multi-page or single-page PDF drawings or high-resolution floor plan images.",
        )
        if uploaded_file is not None:
            doc_stream = uploaded_file.read()
            doc_filename = uploaded_file.name
            doc_type = "pdf" if doc_filename.lower().endswith(".pdf") else "image"
            if len(doc_stream) == 0:
                st.error("Uploaded file is empty (0 bytes). Please upload a valid architectural drawing.")
                return
    else:
        sample_options = [
            "None",
            "MTA 99th St - Sheet A-101 (First Floor Plan)",
            "MTA 99th St - Sheet A-102 (Second Floor Plan)",
            "MTA 99th St - Sheet A-104 (Held-Out Test Set - 69 Verified Walls)",
            "Held-Out Test Set: Spark Lake Grove Permit Set",
            "Sample Tile 01 (Preloaded SegFormer Showcase)",
            "Annotated Spark Test Set (Single Sheet)",
        ]
        sample_choice = st.selectbox("Or choose a pre-loaded drawing", sample_options)

        if sample_choice == "MTA 99th St - Sheet A-101 (First Floor Plan)":
            if DEFAULT_MASTER_PDF_PATH.exists():
                with open(DEFAULT_MASTER_PDF_PATH, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "MTA_99th_St_Master.pdf"
                doc_type = "pdf"
                st.session_state["current_page"] = 14  # A-101 is page index 14
        elif sample_choice == "MTA 99th St - Sheet A-102 (Second Floor Plan)":
            if DEFAULT_MASTER_PDF_PATH.exists():
                with open(DEFAULT_MASTER_PDF_PATH, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "MTA_99th_St_Master.pdf"
                doc_type = "pdf"
                st.session_state["current_page"] = 15  # A-102 is page index 15
        elif sample_choice == "MTA 99th St - Sheet A-104 (Held-Out Test Set - 69 Verified Walls)":
            if DEFAULT_MASTER_PDF_PATH.exists():
                with open(DEFAULT_MASTER_PDF_PATH, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "MTA_99th_St_Master.pdf"
                doc_type = "pdf"
                st.session_state["current_page"] = 17  # A-104 is page index 17
        elif sample_choice == "Held-Out Test Set: Spark Lake Grove Permit Set":
            spark_permit_path = Path(r"C:\Users\TEC ZONE\Downloads\test Spark Lake Grove - Permit Set.pdf")
            if spark_permit_path.exists():
                with open(spark_permit_path, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "Spark_Lake_Grove_Permit_Set.pdf"
                doc_type = "pdf"
                st.session_state["current_page"] = 0
        elif sample_choice == "Sample Tile 01 (Preloaded SegFormer Showcase)":
            sample_img_path = WORKSPACE_ROOT / "drywall_detection" / "checkpoints" / "best_model" / "sample_overlays" / "sample_01_original.png"
            if sample_img_path.exists():
                with open(sample_img_path, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "sample_01_original.png"
                doc_type = "image"
        elif sample_choice == "Annotated Spark Test Set (Single Sheet)":
            spark_path = WORKSPACE_ROOT / "drywall_detection" / "data" / "annotated_spark_test.pdf"
            if spark_path.exists():
                with open(spark_path, "rb") as f:
                    doc_stream = f.read()
                doc_filename = "annotated_spark_test.pdf"
                doc_type = "pdf"
                st.session_state["current_page"] = 0

    if doc_stream is None:
        st.info("👆 Please upload an architectural PDF or select a sample drawing above to begin inspection.")
        render_color_legend()
        return

    # Update session state document
    st.session_state["doc_bytes"] = doc_stream
    st.session_state["doc_name"] = doc_filename

    # --------------------------------------------------------------------------
    # DOCUMENT NAVIGATION & METADATA
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("2. Drawing Navigation & Metadata")

    pdf_doc: Optional[fitz.Document] = None
    num_pages: int = 1

    if doc_type == "pdf":
        if fitz is None:
            st.error("PyMuPDF (fitz) is required to process PDF files.")
            return
        try:
            pdf_doc = fitz.open(stream=doc_stream, filetype="pdf")
            num_pages = len(pdf_doc)
            if num_pages == 0:
                st.error("Uploaded PDF contains zero pages.")
                return
        except Exception as exc:
            st.error(f"Error opening PDF document: {exc}. The file may be corrupt or not a valid PDF.")
            return

        # Page navigation controls
        nav_col1, nav_col2, nav_col3, nav_col4 = st.columns([1, 2, 1, 2])

        if nav_col1.button("⬅️ Previous", disabled=(st.session_state["current_page"] <= 0)):
            st.session_state["current_page"] = max(0, st.session_state["current_page"] - 1)

        st.session_state["current_page"] = nav_col2.selectbox(
            "Select Drawing Sheet",
            options=list(range(num_pages)),
            index=min(st.session_state["current_page"], num_pages - 1),
            format_func=lambda i: f"Page {i+1} of {num_pages}",
        )

        if nav_col3.button("Next ➡️", disabled=(st.session_state["current_page"] >= num_pages - 1)):
            st.session_state["current_page"] = min(num_pages - 1, st.session_state["current_page"] + 1)

        active_page = pdf_doc.load_page(st.session_state["current_page"])
        nav_col4.info(
            f"**Sheet {st.session_state['current_page'] + 1}**: {active_page.rect.width:.0f}x{active_page.rect.height:.0f} pt "
            f"| Rotation: {active_page.rotation}°"
        )
    else:
        try:
            test_img = Image.open(io.BytesIO(doc_stream))
            test_img.verify()
        except Exception as exc:
            st.error(f"Error opening image file: {exc}. The file may be corrupt or not a valid image.")
            return
        st.info(f"Loaded single-image floor plan: `{doc_filename}`")

    # --------------------------------------------------------------------------
    # INFERENCE EXECUTION
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("3. Inference Pipeline Execution")

    exec_col1, exec_col2 = st.columns(2)
    btn_infer_current = exec_col1.button("⚡ Run Inference on Active Sheet", type="primary", use_container_width=True)
    btn_infer_all = exec_col2.button("🚀 Batch Run All Sheets", use_container_width=True, disabled=(doc_type != "pdf" or num_pages <= 1))

    current_idx = st.session_state["current_page"]
    cache_key = f"{doc_filename}_dpi{dpi}_tile{tile_size}"
    if cache_key not in st.session_state["cache"]:
        st.session_state["cache"][cache_key] = {}

    page_cache = st.session_state["cache"][cache_key]

    # Handle single sheet execution
    if btn_infer_current:
        if inferencer is None:
            st.error("Model inferencer is not loaded.")
            return

        with st.status(f"Processing Sheet {current_idx + 1}...", expanded=True) as status:
            t0 = time.time()
            if doc_type == "pdf" and pdf_doc is not None:
                status.write(f"Rendering vector drawing at {dpi} DPI...")
                page_img = render_pdf_page_to_image(pdf_doc, current_idx, dpi=dpi)
            else:
                page_img = Image.open(io.BytesIO(doc_stream)).convert("RGB")

            status.write(f"Executing sliding-window inference ({page_img.width}x{page_img.height} px, tile={tile_size})...")
            mask, probs = inferencer.predict_image_sliding_window(page_img, tile_size=tile_size, overlap=overlap)

            elapsed = time.time() - t0
            stats = compute_takeoff_stats(mask, latency_sec=elapsed)
            stats["page_index"] = current_idx + 1
            stats["sheet_name"] = f"Sheet {current_idx + 1}"

            page_cache[current_idx] = {
                "image": page_img,
                "mask": mask,
                "stats": stats,
            }
            status.update(label=f"✅ Sheet {current_idx + 1} completed in {elapsed:.2f}s!", state="complete")

    # Handle batch all sheets execution
    if btn_infer_all and pdf_doc is not None:
        if inferencer is None:
            st.error("Model inferencer is not loaded.")
            return

        batch_progress = st.progress(0, text="Starting batch inference...")
        for p_i in range(num_pages):
            batch_progress.progress(p_i / num_pages, text=f"Processing Sheet {p_i + 1} of {num_pages}...")
            t0 = time.time()
            p_img = render_pdf_page_to_image(pdf_doc, p_i, dpi=dpi)
            mask, _ = inferencer.predict_image_sliding_window(p_img, tile_size=tile_size, overlap=overlap)
            elapsed = time.time() - t0
            stats = compute_takeoff_stats(mask, latency_sec=elapsed)
            stats["page_index"] = p_i + 1
            stats["sheet_name"] = f"Sheet {p_i + 1}"
            page_cache[p_i] = {
                "image": p_img,
                "mask": mask,
                "stats": stats,
            }
        batch_progress.progress(1.0, text="Batch processing complete!")
        st.success(f"Successfully processed all {num_pages} sheets!")

    # Check if active sheet has cached results
    has_results = current_idx in page_cache

    # --------------------------------------------------------------------------
    # INTERACTIVE VISUAL INSPECTION
    # --------------------------------------------------------------------------
    st.markdown("---")
    st.subheader("4. Interactive Visual Inspection")
    render_color_legend()

    if has_results:
        cached_data = page_cache[current_idx]
        raw_image = cached_data["image"]
        pred_mask = cached_data["mask"]

        # Fast NumPy alpha blend (<50ms)
        overlay_composite = blend_overlay(np.array(raw_image), pred_mask, alpha=alpha)
        mask_rgb = mask_to_rgb(pred_mask)

        tab_overlay, tab_side_by_side, tab_raw_mask = st.tabs([
            "🎨 Annotated Overlay",
            "⚖️ Side-by-Side Comparison",
            "🗺️ Raw Prediction Mask",
        ])

        with tab_overlay:
            st.image(
                overlay_composite,
                caption=f"Annotated Overlay (Sheet {current_idx + 1}, Alpha={alpha:.2f})",
                use_container_width=True,
            )

        with tab_side_by_side:
            s_col1, s_col2 = st.columns(2)
            s_col1.image(raw_image, caption="Original Drawing Linework", use_container_width=True)
            s_col2.image(mask_rgb, caption="4-Class Segmentation Mask", use_container_width=True)

        with tab_raw_mask:
            st.image(mask_rgb, caption="Discrete Material Class Map", use_container_width=True)

        # ----------------------------------------------------------------------
        # SUMMARY ANALYTICS & TAKEOFF DASHBOARD
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.subheader("5. Takeoff Statistics & Material Analytics")

        page_stats = cached_data["stats"]

        # Metric cards with zero-division safety
        m_c1, m_c2, m_c3, m_c4 = st.columns(4)
        m_c1.metric(
            "Total Wall Area",
            f"{page_stats['wall_total_pixels']:,} px",
            delta=f"{page_stats['wall_pct_canvas']}% of sheet",
        )
        m_c2.metric(
            "🟩 Drywall (GWB)",
            f"{page_stats['drywall_pct_walls']}%",
            delta=f"{page_stats['drywall_pixels']:,} px",
        )
        m_c3.metric(
            "🟥 Non-Drywall (CMU/Glass)",
            f"{page_stats['non_drywall_pct_walls']}%",
            delta=f"{page_stats['non_drywall_pixels']:,} px",
        )
        m_c4.metric(
            "🟨 Uncertain / Generic",
            f"{page_stats['uncertain_pct_walls']}%",
            delta=f"{page_stats['uncertain_pixels']:,} px",
        )

        # Detailed Takeoff Table
        tot_px = max(page_stats['total_pixels'], 1)
        takeoff_table_data = [
            {
                "Class ID": 1,
                "Material Class": "Drywall",
                "Color": "#00C853",
                "Pixels": f"{page_stats['drywall_pixels']:,}",
                "Share of Canvas": f"{(page_stats['drywall_pixels'] / tot_px * 100):.2f}%",
                "Share of Walls": f"{page_stats['drywall_pct_walls']}%",
                "Specification Reference": "Verified Gypsum Wallboard (GWB Details 1B-1E, 2B, 3A, 5B, 7A)",
            },
            {
                "Class ID": 2,
                "Material Class": "Non-Drywall",
                "Color": "#D50000",
                "Pixels": f"{page_stats['non_drywall_pixels']:,}",
                "Share of Canvas": f"{(page_stats['non_drywall_pixels'] / tot_px * 100):.2f}%",
                "Share of Walls": f"{page_stats['non_drywall_pct_walls']}%",
                "Specification Reference": f"Detail 1A 6\" CMU Block Masonry Safety Veto; Glass GL1; Conc 11",
            },
            {
                "Class ID": 3,
                "Material Class": "Uncertain",
                "Color": "#FFD600",
                "Pixels": f"{page_stats['uncertain_pixels']:,}",
                "Share of Canvas": f"{(page_stats['uncertain_pixels'] / tot_px * 100):.2f}%",
                "Share of Walls": f"{page_stats['uncertain_pct_walls']}%",
                "Specification Reference": "Generic Partitions / Unassigned Tags / Detail 09 TV Niche (Manual Review)",
            },
            {
                "Class ID": 0,
                "Material Class": "Background",
                "Color": "#FFFFFF",
                "Pixels": f"{page_stats['background_pixels']:,}",
                "Share of Canvas": f"{(page_stats['background_pixels'] / tot_px * 100):.2f}%",
                "Share of Walls": "N/A",
                "Specification Reference": "Architectural Void, Interior Negative Space, Drawing Linework",
            },
        ]
        st.dataframe(takeoff_table_data, use_container_width=True)
        st.caption(f"Inference Latency: {page_stats['latency_sec']}s on {device.upper()}. Resolution: {dpi} DPI.")

        # ----------------------------------------------------------------------
        # EXPORT & DOWNLOAD CAPABILITIES
        # ----------------------------------------------------------------------
        st.markdown("---")
        st.subheader("6. Export & Download Deliverables")

        dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)

        # 1. Download Current Page PNG
        png_buf = io.BytesIO()
        Image.fromarray(overlay_composite).save(png_buf, format="PNG")
        dl_col1.download_button(
            label="🖼️ Download Sheet PNG",
            data=png_buf.getvalue(),
            file_name=f"{Path(doc_filename).stem}_sheet_{current_idx+1}_annotated.png",
            mime="image/png",
            use_container_width=True,
        )

        # 2. Download Annotated PDF (if PDF document)
        if doc_type == "pdf" and fitz is not None:
            masks_to_export = {idx: d["mask"] for idx, d in page_cache.items()}
            annotated_pdf_bytes = build_annotated_pdf_bytes(
                st.session_state["doc_bytes"],
                masks_to_export,
                dpi=dpi,
                alpha=alpha,
            )
            dl_col2.download_button(
                label="📥 Download Annotated PDF",
                data=annotated_pdf_bytes,
                file_name=f"{Path(doc_filename).stem}_annotated.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        else:
            dl_col2.info("PDF download available for PDF inputs.")

        # 3. Download Takeoff CSV
        all_stats = [d["stats"] for d in page_cache.values()]
        csv_str = build_takeoff_csv_str(all_stats)
        dl_col3.download_button(
            label="📊 Download Takeoff CSV",
            data=csv_str,
            file_name=f"{Path(doc_filename).stem}_takeoff.csv",
            mime="text/csv",
            use_container_width=True,
        )

        # 4. Download Summary JSON
        summary_payload = {
            "document_name": doc_filename,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model_architecture": "segformer_b0",
            "device": device,
            "dpi": dpi,
            "alpha": alpha,
            "reference_set_disclosure": REFERENCE_SET_NOTICE,
            "processed_pages": all_stats,
        }
        json_str = json.dumps(summary_payload, indent=2)
        dl_col4.download_button(
            label="📄 Download Summary JSON",
            data=json_str,
            file_name=f"{Path(doc_filename).stem}_summary.json",
            mime="application/json",
            use_container_width=True,
        )

    else:
        # Drawing loaded but not yet inferred
        if doc_type == "pdf" and pdf_doc is not None:
            preview_img = render_pdf_page_to_image(pdf_doc, current_idx, dpi=min(dpi, 100))
        else:
            preview_img = Image.open(io.BytesIO(doc_stream)).convert("RGB")

        st.image(preview_img, caption=f"Original Drawing Preview (Sheet {current_idx + 1}) — Click 'Run Inference' above", use_container_width=True)


if __name__ == "__main__":
    main()
