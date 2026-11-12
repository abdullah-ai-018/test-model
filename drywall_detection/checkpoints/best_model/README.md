# Champion Model Delivery: SegFormer-B0 Architectural Wall Detector

**Milestone**: M4 — Wall Segmentation Training & Model Delivery  
**Package Path**: `drywall_detection/checkpoints/best_model/`  
**Model Name**: `drywall_segformer_b0`  
**Architecture**: Hierarchical Mix Transformer (MiT-B0) with All-MLP Decoder  
**Target Taxonomy**: 4-Class Architectural Wall Segmentation  

---

## Mandatory Notice — Progress Set & Single-Project Bounds
> The reference PDF represents MTA Contract C-48526 (99th Street Phase 2 Interior Set). It is explicitly stamped "PROGRESS SET 95% CDs 10/02/2026" and constitutes an interim construction design progress set, not an approved final as-built construction document. All 71 pages originate from a single building facility and serve strictly as a single-project calibration sample. Empirical results on this drawing set cannot prove cross-domain generalization.

---

## 1. Overview & Architectural Specifications

This checkpoint bundle packages the champion semantic segmentation model evaluated and delivered under Milestone M4. The model detects structural walls and classifies partitions into verified gypsum drywall assemblies, non-drywall assemblies, and uncertain partitions on architectural drawings and multi-page PDFs.

### Architectural Parameters:
- **Architecture**: SegFormer-B0 (`transformers.SegformerForSemanticSegmentation`)
- **Encoder**: MiT-B0 hierarchical vision transformer (4 stages: depths `[2, 2, 2, 2]`, channels `[32, 64, 160, 256]`, patch strides `[4, 2, 2, 2]`)
- **Decoder**: Lightweight All-MLP projection head fusing multi-scale feature maps at $C_{dec}=256$
- **Total Parameters**: **3,715,172 (~3.72M)**
- **Trainable Parameters**: **3,715,172**
- **Model Checkpoint Size**: **14.17 MB** (float32 state dictionary in `best_model.pt`)
- **Empirical CPU Forward Latency (Batch=2, 256x256)**: **~635 ms** (1.58 FPS)
- **FLOPs (256x256)**: **3.50 GFLOPs**

### 10-Line PyTorch Minimal Reproduction Snippet:
```python
import torch, json
from drywall_detection.models.segformer import SegFormerB0

# 1. Instantiate offline model and load weights
model = SegFormerB0(num_classes=4, offline=True)
ckpt = torch.load("drywall_detection/checkpoints/best_model/best_model.pt", map_location="cpu")
model.load_state_dict(ckpt["model_state_dict"])
model.eval()

# 2. Run inference on input image tensor [1, 3, 256, 256]
x = torch.randn(1, 3, 256, 256)
with torch.no_grad():
    logits = model(x)  # [1, 4, 256, 256]
    pred_mask = torch.argmax(logits, dim=1)  # [1, 256, 256]
```

---

## 2. 4-Class Segmentation Taxonomy

The model predicts pixel-level class assignments matching the project's strict classification guardrails:

| Class Index | Class Name | Color Code | Hex Code | Description & Assemblies |
|:---:|:---:|:---:|:---:|---|
| **0** | **Background** | Canvas / Transparent | `#FFFFFF` | Non-wall canvas, room voids, dimension strings, annotations, text. |
| **1** | **Drywall** | Green | `#00C853` | Verified Gypsum Wallboard (GWB) partitions (Details 1B-1E, 2B-2C, 3A, 3D, 5B, 5D, 5E, 7A-7C, 7E-7G, 8A, 10). |
| **2** | **Non-Drywall** | Red | `#D50000` | Verified non-drywall partitions: 6" CMU block masonry (Detail 1A mandatory safety veto), concrete columns (11), glass systems (GL1, GL2). |
| **3** | **Uncertain** | Yellow | `#FFD600` | Ambiguous partitions, unassigned linework, millwork/niches (Detail 09), generic exterior walls lacking verified schedules. |

---

## 3. Training & Calibration Configuration

The model was calibrated using the low-memory Tier 5 CPU training engine with strict drawing-level split isolation:
- **Loss Function**: `CompoundLoss` ($\alpha = 1.0, \beta = 1.0$)
  $$\mathcal{L}_{\text{Compound}} = 1.0 \cdot \mathcal{L}_{\text{Dice}} + 1.0 \cdot \mathcal{L}_{\text{Focal}}$$
- **SoftDiceLoss**: Squared denominator ($\sum p^2 + \sum y^2$) for sharper gradients on thin wall linework.
- **FocalLoss**: Numerically stabilized with $\log\text{-softmax}$ and tensor $\text{gather}$, $\gamma = 2.0$ dynamic modulating factor.
- **Optimizer**: AdamW ($\beta_1=0.9, \beta_2=0.999$, weight decay $10^{-2}$, initial learning rate $10^{-4}$)
- **Scheduler**: Cosine Annealing learning rate schedule down to $\eta_{min}=10^{-6}$
- **Hardware Tier**: Tier 5 Local Host (Windows 10, Intel Core 4P/8L, batch size $B=2$, gradient accumulation $N=8$, effective batch size $B_{eff}=16$, $256 \times 256$ input resolution, `num_workers=0`, `torch.set_num_threads(4)`).
- **Weak Pseudo-Label Quarantine**: Factor $\lambda = 0.35$ discount on pseudo-labeled tiles; strictly excluded from validation and test splits.

---

## 4. Standalone Offline Inference (`infer.py`)

The included `infer.py` script is self-contained and operates completely offline without downloading external weights.

### Command-Line Arguments:
- `--image`, `--input`, `-i`: Path to input image (`.png`, `.jpg`) or architectural drawing PDF (`.pdf`). **[Required]**
- `--output`, `-o`: Path to output annotated image (`.png`) or multi-page annotated PDF (`.pdf`).
- `--checkpoint`, `-c`: Path to checkpoint file or directory (default: current directory containing `infer.py`).
- `--page`, `-p`: Zero-based page index to process if input is a PDF (default: process all pages).
- `--dpi`: Rendering resolution in DPI for PDF pages (default: `150`).
- `--device`, `-d`: Target execution device (`cpu` or `cuda`, auto-detected by default).
- `--alpha`: Alpha transparency for wall annotation blending (default: `0.45`).
- `--mode`: Output mode: `overlay` (default) or `mask` (8-bit single-channel indexed PNG).

### Usage Examples:

```powershell
# Display CLI help
python infer.py --help

# Predict on an image using --image and --checkpoint
python infer.py --image path/to/floorplan.png --output annotated_overlay.png --checkpoint best_model.pt

# Predict on a PDF page with Hann window apodization
python infer.py --image "sample_drawing.pdf" --page 0 --output annotated_page_0.png --dpi 150
```

---

## 5. Google Colab GPU Accelerated Training

For high-throughput training on NVIDIA Tesla T4 GPUs:
1. Open Google Colab and set Runtime to **GPU (Tesla T4)**.
2. Clone repository or upload `drywall_detection/` and `train_colab.py`.
3. Run the automated standalone training runner:
```bash
!python train_colab.py --epochs 25 --batch-size 8
```
4. Checkpoints and evaluation metrics will be exported directly to `drywall_detection/checkpoints/best_model/`.

---

## 6. Bundle Manifest (All 8 Required Artifacts)

```
drywall_detection/checkpoints/best_model/
├── best_model.pt           # 1. PyTorch model weights & state dictionary
├── config.json             # 2. Architecture, hyperparameters, normalization, inference settings
├── class_mapping.json      # 3. Canonical 4-class taxonomy, colors, descriptions, id2label, label2id
├── training_log.json       # 4. Epoch-by-epoch loss & validation metrics history
├── metrics.json            # 5. Final held-out evaluation metrics on validation/test split
├── infer.py                # 6. Standalone offline inference CLI reload-and-infer runner
├── README.md               # 7. Model card, specifications, benchmarks, and Colab instructions
└── sample_overlays/        # 8. Visual inspection triplets (sample_01_original, mask, overlay)
    ├── sample_01_original.png
    ├── sample_01_mask.png
    └── sample_01_overlay.png
```
├── metrics.json            # Final held-out evaluation metrics on test.json
├── infer.py                # Standalone offline inference CLI script
├── README.md               # Model documentation and invocation instructions
└── sample_overlays/        # Visual prediction comparisons on held-out drawings
```

---

## 6. Progress Set Limitations & Scope

In accordance with project integrity standards:
1. **95% Construction Documents Status**: Models calibrated against MTA 99th Street drawings reflect a 95% CDs progress set. Linework and wall geometries represent progress documentation rather than final 100% as-built conditions.
2. **Single-Project Calibration**: All models trained on this split represent a single-project calibration sample. Generalization to unseen drawing styles with radically different lineweights, scales, or vector layering will require transfer learning or additional training samples.
