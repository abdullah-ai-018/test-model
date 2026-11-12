# Dispatch: Milestone M3 Architecture Explorer (`m3_explorer_1`)

## Mission
Investigate and benchmark candidate semantic segmentation architectures (SegFormer-B0 vs lightweight U-Net) for wall detection and drywall classification on architectural drawing tiles, establishing architectural specifications, model interfaces, parameter counts, memory footprints, and dependency compatibility.

## Reference Documents (MUST READ FIRST)
1. `ORIGINAL_REQUEST.md` (Workspace root: `c:\Users\TEC ZONE\OneDrive\Desktop\test-model\ORIGINAL_REQUEST.md`)
2. `PROJECT.md` (`c:\Users\TEC ZONE\OneDrive\Desktop\test-model\.agents\teamwork\PROJECT.md`) - specifically Section 1 Track 3, Section 2 Feature Inventory (F-MODEL-ARCH, F-MODEL-COMPARE), Section 4.4 Model Checkpoint Contract, and Section 5 Code Layout.
3. `drywall_detection/datasets/unified_format.py` (Tile dimensions: 512x512, Mode 'P' 8-bit indexed, 4-class taxonomy: 0=Background, 1=Drywall, 2=Non-Drywall, 3=Uncertain).
4. `drywall_detection/datasets/loader.py` (PyTorch Dataset & streaming DataLoader).
5. `drywall_detection/data/processed/splits/splits_summary.json` (Split manifests and tile counts).

## Tasks & Scope
1. **Dependency & Environment Audit**:
   - Inspect Python environment for available ML packages: PyTorch (`torch`), `torchvision`, `timm`, `transformers` (HuggingFace), `segmentation_models_pytorch` (smp), `scipy`, etc.
   - Determine if SegFormer-B0 can be loaded via HuggingFace `transformers.SegformerForSemanticSegmentation.from_pretrained("nvidia/mit-b0")` (or offline fallback architecture) and if lightweight U-Net can be constructed with `torchvision` ResNet backbones or custom PyTorch implementation.
2. **Architecture Specification**:
   - **Candidate 1: SegFormer-B0**: Mix Transformer (MiT) hierarchical encoder + all-MLP decoder. Input $3 \times 512 \times 512$, output $4 \times 512 \times 512$ (or $4 \times 128 \times 128$ upsampled via bilinear interpolation to $512 \times 512$). Measure parameters (~3.7M) and FLOPs.
   - **Candidate 2: Lightweight U-Net**: ResNet18/ResNet34 encoder or custom 4-stage convolutional encoder-decoder with skip connections. Input $3 \times 512 \times 512$, output $4 \times 512 \times 512$. Measure parameters (~14M-21M) and memory footprint.
3. **Interface & Contract Design**:
   - Define exact signatures for:
     - `drywall_detection/models/segformer.py` (`build_segformer(num_classes=4, pretrained=True, in_channels=3) -> nn.Module`)
     - `drywall_detection/models/unet.py` (`build_unet(num_classes=4, backbone="resnet18", pretrained=True, in_channels=3) -> nn.Module`)
     - `drywall_detection/models/__init__.py`
   - Ensure forward pass takes `[B, 3, 512, 512]` float tensor (normalized with ImageNet mean/std or drawing mean/std) and returns `[B, 4, 512, 512]` logits tensor.
4. **Offline & Low-Memory Resilience**:
   - Provide offline initialization mechanisms in case HuggingFace Hub cannot be reached (e.g., local random weight initialization fallback with graceful warning, or pretrained weight caching).
   - Verify peak memory consumption during forward/backward pass with `batch_size=2` on CPU fits comfortably within 1.0 GB available RAM.

## Deliverables
- Write detailed investigation and architectural specification to `.agents/teamwork/m3_explorer_1/analysis.md`.
- Write self-contained handoff report to `.agents/teamwork/m3_explorer_1/handoff.md` following the Handoff Protocol (Observation, Logic Chain, Caveats, Conclusion, Verification Method).
- Notify orchestrator with summary upon completion.
