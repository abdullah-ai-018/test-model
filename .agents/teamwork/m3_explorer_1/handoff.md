# Milestone M3 Model Architecture Exploration Handoff Report

**Agent**: `m3_explorer_1` (Model Architecture Explorer)  
**Recipient**: `parent` (Milestone M3 Orchestrator / Implementer `m3_builder_1`)  
**Date**: 2026-11-09T00:06:00Z  
**Type**: Hard Handoff (Investigation & Architecture Specification Complete)  

---

## 1. Observation

Direct empirical observations from tool executions and environment profiling:

1. **Python ML Environment Audit**:
   - `python -c "import torch, torchvision, transformers, timm; ..."`:
     - `torch`: `2.1.0+cpu` (CUDA unavailable)
     - `torchvision`: `0.16.0+cpu`
     - `transformers`: `4.41.2`
     - `timm`: `1.0.22`
     - `scipy`: `1.15.3`
     - `shapely`: `2.1.1`
     - `cv2`: `4.11.0`
     - `PIL`: `10.2.0`
     - `segmentation_models_pytorch`: **NOT INSTALLED** (`No module named 'segmentation_models_pytorch'`).

2. **Network / Hub Reachability**:
   - Running `transformers.SegformerForSemanticSegmentation.from_pretrained('nvidia/mit-b0')` triggered:
     ```
     '(ReadTimeoutError("HTTPSConnectionPool(host='us.aws.cdn.hf.co', port=443): Read timed out. (read timeout=10)"), ...)' thrown while requesting GET https://huggingface.co/nvidia/mit-b0/resolve/main/pytorch_model.bin
     ```
   - HuggingFace Hub model weight downloading cannot be relied upon in offline/firewalled environments without local fallback.

3. **Candidate 1: SegFormer-B0 Empirical Benchmarks**:
   - Instantiated via `SegformerConfig` with MiT-B0 specifications (`depths=[2, 2, 2, 2]`, `hidden_sizes=[32, 64, 160, 256]`, `decoder_hidden_size=256`):
     - Total Parameters: **3,715,172 (~3.72M)**
     - Trainable Parameters: **3,715,172**
     - Weight Size on Disk: **14.17 MB**
     - Raw Output Logits Shape: `torch.Size([2, 4, 128, 128])` (downscaled $4\times$ from input $512 \times 512$)
     - Bilinear Interpolated Logits Shape: `torch.Size([2, 4, 512, 512])`
     - Measured Average CPU Forward Time ($B=2$): **2.6151 s**
     - Measured Average CPU Backward Time ($B=2$): **10.8835 s**
     - Peak Traced Heap Memory: **0.70 MB** (Total resident RSS < 200 MB)

4. **Candidate 2: Lightweight ResNet18 U-Net Empirical Benchmarks**:
   - Instantiated using native `torchvision.models.resnet18(weights=None)` encoder + 4-stage symmetrical convolutional decoder:
     - Total Parameters: **14,343,524 (~14.34M)**
     - Weight Size on Disk: **54.72 MB**
     - Raw Output Logits Shape: `torch.Size([2, 4, 512, 512])`
     - Measured Average CPU Forward Time ($B=2$): **4.7673 s**
     - Measured Average CPU Backward Time ($B=2$): **9.3924 s**
     - Peak Traced Heap Memory: **0.03 MB** (Total resident RSS < 250 MB)

5. **Candidate 2b & 2c Variants**:
   - ResNet34 U-Net: **24,451,684 parameters**, **93.28 MB**, Forward Time: **5.9537 s**, Backward Time: **11.2001 s**.
   - Custom 4-stage Conv U-Net (`base_ch=16`): **1,942,628 parameters**, **7.41 MB**, Forward Time: **3.1255 s**.

6. **DataLoader Streaming Ingestion**:
   - `drywall_detection/datasets/loader.py:get_tile_dataloader` tested against `drywall_detection/data/processed/splits/train.json`:
     - Output: `images=torch.Size([2, 3, 512, 512])`, dtype `torch.float32`, range `[-2.118, +2.640]`
     - Output: `masks=torch.Size([2, 512, 512])`, dtype `torch.int64`, classes `{0, 1, 3}` present.
   - Validation split (`val.json`): 1 batch ($B=2$).
   - Test split (`test.json`): 28 batches ($B=2$, 55 tiles).

---

## 2. Logic Chain

1. **Premise 1**: The training and deployment environment is Windows CPU with 1.0 GB RAM budget and no GPU acceleration (`torch.cuda.is_available() == False`).
2. **Premise 2**: Architectural floor plans feature thin, elongated walls traversing hundreds of pixels across $512 \times 512$ tiles, which benefits strongly from non-local multi-scale receptive fields.
3. **Inference from Observation 1 & 2**: Because `segmentation_models_pytorch` is missing and Hugging Face Hub encounters read timeouts, both model architectures must provide fully offline, native implementations (via `transformers.SegformerConfig` and native `torchvision.models.resnet18/34`).
4. **Inference from Observation 3 & 4**: SegFormer-B0 possesses 3.72M parameters vs 14.34M for ResNet18 U-Net (a 74% parameter reduction). On CPU inference, SegFormer-B0 executes forward pass in 2.615s vs 4.767s for ResNet18 U-Net (1.82x faster inference).
5. **Inference from Observation 3**: The raw SegFormer decoder outputs downsampled logits `[B, 4, 128, 128]`. To strictly satisfy the interface contract and allow seamless compound loss calculation with `[B, 512, 512]` ground truth masks, a bilinear interpolation layer to `[B, 4, 512, 512]` must be incorporated into `SegFormerWallDetector.forward()`.
6. **Inference from Observation 3 & 4**: Both architectures require less than 300 MB total resident RAM during forward and backward passes with batch size 2, providing a >70% safety margin under the 1.0 GB RAM constraint.
7. **Synthesis Conclusion**: SegFormer-B0 is the superior champion candidate for architectural wall segmentation, with ResNet18 U-Net providing an indispensable native baseline.

---

## 3. Caveats

1. **Backbone Pretrained Weights**: Because the live Hugging Face Hub download timed out on `us.aws.cdn.hf.co`, initial training will operate with random initialization unless cached weights are supplied locally or external connectivity is established.
2. **CPU Training Epoch Time**: With 8 training samples ($B=2 \implies 4$ steps/epoch) and a backward step latency of ~10.8s, one full training epoch on CPU will require approximately $\sim 45\text{ seconds}$. A 5-epoch benchmark training run will take $\sim 3.75\text{ minutes}$.
3. **95% CD Status Limitation**: In accordance with Project Rule 5, all models calibrated or evaluated against MTA 99th Street data reflect a 95% Construction Documents progress set and represent a single-project calibration sample.

---

## 4. Conclusion

1. **Primary Champion Architecture**: **SegFormer-B0** (`drywall_detection/models/segformer.py`).
   - 3,715,172 parameters, 14.17 MB model size, 2.615s forward latency on CPU, global multi-head self-attention.
2. **Secondary Baseline Architecture**: **ResNet18 U-Net** (`drywall_detection/models/unet.py`).
   - 14,343,524 parameters, 54.72 MB model size, 4.767s forward latency on CPU, native PyTorch/TorchVision implementation.
3. **Loss Function**: **Compound Soft Dice + Focal Loss** (`CompoundDiceFocalLoss(dice_weight=0.5, focal_weight=0.5)`) to counteract the 90:10 background-to-wall class imbalance.
4. **Evaluation Engine**: Vectorized `SegmentationMetricTracker` computing mIoU, Wall IoU, Dice/F1, Precision, Recall, and Boundary IoU.
5. **Checkpoint Directory**: `drywall_detection/checkpoints/best_model/` storing `best_model.pt`, `config.json`, `class_mapping.json`, `training_log.json`, `metrics.json`, `infer.py`, `README.md`, and `sample_overlays/`.

---

## 5. Verification Method

To independently verify all findings and benchmarks reported:

1. **Verify Package Availability & Parameter Counts**:
   ```powershell
   python -c "from transformers import SegformerConfig, SegformerForSemanticSegmentation; import torchvision.models as m; c = SegformerConfig(num_labels=4, num_channels=3, depths=[2, 2, 2, 2], hidden_sizes=[32, 64, 160, 256], decoder_hidden_size=256); s = SegformerForSemanticSegmentation(c); print('SegFormer params:', sum(p.numel() for p in s.parameters())); print('ResNet18 params:', sum(p.numel() for p in m.resnet18(weights=None).parameters()))"
   ```
   *Expected Output*: `SegFormer params: 3715172`, `ResNet18 params: 11689512`.

2. **Verify SegFormer Forward Pass & Upsampling**:
   ```powershell
   python -c "import torch, torch.nn.functional as F; from transformers import SegformerConfig, SegformerForSemanticSegmentation; m = SegformerForSemanticSegmentation(SegformerConfig(num_labels=4, num_channels=3, depths=[2, 2, 2, 2], hidden_sizes=[32, 64, 160, 256], decoder_hidden_size=256)); x = torch.randn(2, 3, 512, 512); logits = F.interpolate(m(x).logits, size=(512, 512), mode='bilinear'); assert logits.shape == (2, 4, 512, 512); print('SegFormer shape check passed:', logits.shape)"
   ```
   *Expected Output*: `SegFormer shape check passed: torch.Size([2, 4, 512, 512])`.

3. **Verify DataLoader Streaming**:
   ```powershell
   python -c "from pathlib import Path; from drywall_detection.datasets.loader import get_tile_dataloader; l = get_tile_dataloader(Path('drywall_detection/data/processed/splits/train.json'), batch_size=2); imgs, msks = next(iter(l)); assert imgs.shape == (2, 3, 512, 512) and msks.shape == (2, 512, 512); print('DataLoader shape check passed!')"
   ```
   *Expected Output*: `DataLoader shape check passed!`.

4. **Invalidation Conditions**:
   - SegFormer parameter count deviates from 3,715,172.
   - Forward pass on $2 \times 3 \times 512 \times 512$ tensor exceeds 500 MB memory consumption.
   - SegFormer logits cannot be interpolated to $(512, 512)$.
