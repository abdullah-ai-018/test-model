# Defect Analysis & Remediation Strategy: Milestone M3 Iteration 2

**Author**: `m3_iter2_explorer_1` (CLI & Checkpoint Remediation Explorer)  
**Date**: 2026-11-09T06:30:00Z  
**Target Milestone**: Milestone M3 (Iteration 2 Remediation)  
**Status**: Completed Analysis & Proposed Solutions  

---

## 1. Executive Summary

Milestone M3 Reviewer (`m3_reviewer_1`) issued a **REQUEST_CHANGES** verdict due to 4 identified defects regarding `drywall_detection/checkpoints/best_model/infer.py`, checkpoint metadata alignment, and test suite coverage.

This investigation conducted empirical reproductions, root-cause analyses, and formulated exact, verified remediation strategies for the implementation worker:

1. **Defect 1 (Missing `import time` in `infer.py`)**:
   - *Status*: Verified. In `infer.py`, lines 355, 375, and 407 invoke `time.time()`. While `import time` was inserted at line 28 in recent workspace state, the CLI entrypoint was previously untested in automated CI, which allowed this regression to manifest. Running `python infer.py --input ...` now executes cleanly with `import time` present.
2. **Defect 2 (CLI Subprocess Test Coverage Gap)**:
   - *Status*: Verified. `drywall_detection/tests/test_models.py` previously tested `StandaloneInferencer` exclusively via Python in-memory method invocations, omitting CLI invocation.
   - *Remediation*: Designed `test_infer_cli_invocation(tmp_path)` using `subprocess.run([sys.executable, str(infer_script), ...])` to test `--help` and single-tile image CLI processing with JSON summary validation.
3. **Defect 3 (Resolution Metadata Alignment)**:
   - *Status*: Verified. `config.json` declared `input_size: [256, 256]` and `tile_size: 256`, whereas `DrywallTileDataset` in `loader.py` and `unified_format.py` produce 512x512 tiles, and `infer.py` hardcoded 512.
   - *Remediation*: Synchronize `config.json` to `tile_size: 512`, `input_size: [512, 512]`, and update `infer.py` to dynamically bind `self.tile_size = int(self.config.get("tile_size") or 512)` instead of hardcoded constants. Also update `trainer.py` to write 512.
4. **Defect 4 (Sliding Window Canvas Bounds Guard for Small Images)**:
   - *Status*: Empirically Reproduced. When `image.width < tile_size` or `image.height < tile_size` (e.g. 256x256), `predict_image_sliding_window` crashed with `ValueError: operands could not be broadcast together with shapes (256,256,4) (512,512,4)`.
   - *Remediation*: Implemented an automatic white canvas padding guard at the entrypoint of `predict_image_sliding_window` that pads small images to `max(dim, tile_size)`, executes inference, and crops the output back to original image dimensions. Added dedicated unit test `test_standalone_inferencer_small_canvas_guard()`.

---

## 2. Detailed Defect Analysis & Exact Remediation

### Defect 1: Missing `import time` in `infer.py`

#### Observation & Root Cause
- In `drywall_detection/checkpoints/best_model/infer.py`:
  - Line 355: `t0 = time.time()`
  - Line 375: `summary_stats["elapsed_sec"] = round(time.time() - t0, 3)`
  - Line 407: `summary_stats["elapsed_sec"] = round(time.time() - t0, 3)`
- In the initial commit, `import time` was omitted from standard library imports (lines 20–30), causing:
  ```text
  NameError: name 'time' is not defined at line 354, in main
  ```
- Current workspace check confirms line 28 contains `import time`. Running:
  ```powershell
  python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
  ```
  successfully exits with code 0 in ~22.9s and outputs valid JSON.

#### Action for Implementer
- Retain `import time` at line 28 in `drywall_detection/checkpoints/best_model/infer.py`.
- Ensure imports follow standard library grouping order.

---

### Defect 2: CLI Subprocess Test Coverage Gap

#### Observation & Root Cause
- `drywall_detection/tests/test_models.py` had 17 passing tests, but all inferencer tests were in-memory unit tests (`test_standalone_inferencer_tile_and_sliding_window`).
- `test_models.py` had zero tests invoking `infer.py` via `subprocess.run()`.
- Consequently, top-level scope or CLI entrypoint `main()` errors (`argparse` issues, missing CLI imports, unhandled exceptions) could pass CI completely unnoticed.

#### Proposed Test Implementation
Add two test functions to Test Group 6 in `drywall_detection/tests/test_models.py`:

```python
def test_infer_cli_invocation(tmp_path):
    """Verifies standalone infer.py CLI execution via subprocess with --help and image input."""
    import subprocess
    import sys

    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    infer_script = ckpt_dir / "infer.py"
    if not infer_script.exists():
        pytest.skip("infer.py not found")

    # 1. Test --help invocation
    help_cmd = [sys.executable, str(infer_script), "--help"]
    res_help = subprocess.run(help_cmd, capture_output=True, text=True)
    assert res_help.returncode == 0
    assert "Standalone offline inference CLI" in res_help.stdout
    assert "--input" in res_help.stdout or "--image" in res_help.stdout

    # 2. Test single tile CLI invocation (512x512 tile)
    test_img_path = tmp_path / "test_tile.png"
    out_overlay_path = tmp_path / "test_out_overlay.png"
    Image.new("RGB", (512, 512), color=(255, 255, 255)).save(test_img_path)

    cmd = [
        sys.executable,
        str(infer_script),
        "--input", str(test_img_path),
        "--output", str(out_overlay_path),
        "--checkpoint", str(ckpt_dir),
        "--device", "cpu",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"infer.py CLI failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    assert out_overlay_path.exists(), "Output overlay image was not created by CLI"
    assert out_overlay_path.stat().st_size > 0

    # Parse stdout summary stats JSON
    json_start = res.stdout.find("{")
    assert json_start != -1, f"No JSON found in stdout:\n{res.stdout}"
    summary = json.loads(res.stdout[json_start:])
    assert summary["status"] == "success"
    assert summary["type"] == "image"
    assert summary["dimensions"] == [512, 512]
    assert "pixel_counts" in summary
    assert "elapsed_sec" in summary
```

---

### Defect 3: Resolution Metadata Alignment

#### Observation & Root Cause
- In `drywall_detection/checkpoints/best_model/config.json`:
  ```json
  "input_size": [256, 256],
  "input_resolution": [256, 256],
  "tile_size": 256,
  "tile_overlap": 64,
  ```
- In `drywall_detection/checkpoints/best_model/infer.py`:
  - `create_hann_window(tile_size: int = 512)`
  - `self.hann_window = create_hann_window(512)`
  - Hardcoded resize to `(512, 512)`.
- In `drywall_detection/datasets/loader.py`:
  - Dataset tiles are defined as 512x512:
    `if image.size != (512, 512): image = image.resize((512, 512), Image.BILINEAR)`
- In `drywall_detection/models/trainer.py`:
  - Lines 422, 438–441 hardcode `256` into the saved checkpoint metadata dictionary.

#### Action for Implementer
1. **Update `config.json`**:
   Set `tile_size` to 512, `input_size` to `[512, 512]`, `input_resolution` to `[512, 512]`, and `tile_overlap` to 102.
2. **Update `trainer.py`**:
   Change lines 422 and 438–441 to default to 512:
   ```python
   "input_size": [512, 512],
   "input_resolution": [512, 512],
   "tile_size": 512,
   "tile_overlap": 102,
   ```
3. **Dynamic parameter resolution in `infer.py`**:
   In `StandaloneInferencer.__init__`:
   ```python
   self.tile_size = int(self.config.get("tile_size") or 512)
   self.hann_window = create_hann_window(self.tile_size)
   ```
   In `predict_tile`:
   ```python
   target_size = (self.tile_size, self.tile_size)
   if tile_img.size != target_size:
       tile_img = tile_img.resize(target_size, Image.BILINEAR)
   ```
   In `predict_image_sliding_window`:
   ```python
   def predict_image_sliding_window(
       self,
       image: Image.Image,
       tile_size: Optional[int] = None,
       overlap: float = 0.2,
   ) -> Tuple[np.ndarray, np.ndarray]:
       actual_tile_size = tile_size if tile_size is not None else self.tile_size
       hann = self.hann_window if actual_tile_size == self.tile_size else create_hann_window(actual_tile_size)
   ```

---

### Defect 4: Sliding Window Canvas Bounds Guard for Small Images

#### Observation & Root Cause
- When an input image has dimensions smaller than `tile_size` (e.g. 256x256 or 300x700 with `tile_size=512`):
  - `prob_canvas` is initialized to `(height, width, 4)`.
  - When `height < tile_size`, `y_coords = [0]`.
  - `crop = img_rgb.crop((0, 0, 512, 512))` expands with black pixels to 512x512.
  - The model outputs `probs` of shape `(512, 512, 4)`.
  - At line 226:
    ```python
    prob_canvas[y : y + tile_size, x : x + tile_size] += weighted_probs
    ```
    `prob_canvas[0:512, 0:512]` is truncated by slice bounds to `(256, 256, 4)`.
    NumPy fails with:
    `ValueError: operands could not be broadcast together with shapes (256,256,4) (512,512,4) (256,256,4)`

#### Action for Implementer
Add canvas bounds guard at the top of `predict_image_sliding_window`:
```python
        img_rgb = image.convert("RGB")
        width, height = img_rgb.size
        actual_tile_size = tile_size if tile_size is not None else self.tile_size

        # Guard for small canvases: if smaller than tile_size in either dimension,
        # pad canvas with white (standard drawing background) and crop results back.
        if width < actual_tile_size or height < actual_tile_size:
            pad_w = max(width, actual_tile_size)
            pad_h = max(height, actual_tile_size)
            padded_img = Image.new("RGB", (pad_w, pad_h), color=(255, 255, 255))
            padded_img.paste(img_rgb, (0, 0))
            full_mask, full_probs = self.predict_image_sliding_window(
                padded_img,
                tile_size=actual_tile_size,
                overlap=overlap,
            )
            return full_mask[:height, :width], full_probs[:height, :width]
```

Add dedicated unit test to `test_models.py`:
```python
def test_standalone_inferencer_small_canvas_guard():
    """Verifies predict_image_sliding_window gracefully handles canvases smaller than tile_size."""
    ckpt_dir = Path("drywall_detection/checkpoints/best_model")
    if not (ckpt_dir / "best_model.pt").exists():
        pytest.skip("best_model checkpoint not yet created.")

    inferencer = StandaloneInferencer(checkpoint_dir=ckpt_dir, device="cpu")

    # Image smaller than tile_size in both dimensions (256x256 vs tile_size 512)
    small_img = Image.new("RGB", (256, 256), color=(255, 255, 255))
    mask_small, probs_small = inferencer.predict_image_sliding_window(small_img, tile_size=512)
    assert mask_small.shape == (256, 256)
    assert probs_small.shape == (256, 256, 4)

    # Image smaller in one dimension only (300x700)
    rect_img = Image.new("RGB", (300, 700), color=(255, 255, 255))
    mask_rect, probs_rect = inferencer.predict_image_sliding_window(rect_img, tile_size=512)
    assert mask_rect.shape == (700, 300)
    assert probs_rect.shape == (700, 300, 4)
```

---

## 3. Concrete Code Snippets (Before -> After)

### File 1: `drywall_detection/checkpoints/best_model/infer.py`

#### Change 1.1: StandaloneInferencer initialization and dynamic tile_size
**Before (lines 96-98)**:
```python
        self.config, self.class_mapping = self._load_metadata()
        self.model = self._load_model()
        self.hann_window = create_hann_window(512)
```
**After**:
```python
        self.config, self.class_mapping = self._load_metadata()
        self.model = self._load_model()
        self.tile_size = int(self.config.get("tile_size") or 512)
        self.hann_window = create_hann_window(self.tile_size)
```

#### Change 1.2: predict_tile size alignment
**Before (lines 152-154)**:
```python
        if tile_img.size != (512, 512):
            tile_img = tile_img.resize((512, 512), Image.BILINEAR)
```
**After**:
```python
        target_size = (self.tile_size, self.tile_size)
        if tile_img.size != target_size:
            tile_img = tile_img.resize(target_size, Image.BILINEAR)
```

#### Change 1.3: predict_image_sliding_window small canvas guard and parameter resolution
**Before (lines 171-197)**:
```python
    @torch.no_grad()
    def predict_image_sliding_window(
        self,
        image: Image.Image,
        tile_size: int = 512,
        overlap: float = 0.2,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs sliding-window inference with Hann window apodization stitching.

        Args:
            image: Full-scale PIL Image (any dimension).
            tile_size: Size of tile square (512).
            overlap: Overlap fraction (0.2 -> 20% overlap).

        Returns:
            mask_uint8: [H, W] predicted class indices in {0, 1, 2, 3}.
            probs: [H, W, 4] smoothed class probabilities.
        """
        img_rgb = image.convert("RGB")
        width, height = img_rgb.size

        # If exactly tile size, predict directly
        if width == tile_size and height == tile_size:
            mask = self.predict_tile(img_rgb)
            probs = np.eye(4)[mask].astype(np.float32)
            return mask, probs

        stride = int(tile_size * (1.0 - overlap))
```
**After**:
```python
    @torch.no_grad()
    def predict_image_sliding_window(
        self,
        image: Image.Image,
        tile_size: Optional[int] = None,
        overlap: float = 0.2,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Performs sliding-window inference with Hann window apodization stitching.

        Args:
            image: Full-scale PIL Image (any dimension).
            tile_size: Size of tile square (defaults to self.tile_size).
            overlap: Overlap fraction (0.2 -> 20% overlap).

        Returns:
            mask_uint8: [H, W] predicted class indices in {0, 1, 2, 3}.
            probs: [H, W, 4] smoothed class probabilities.
        """
        actual_tile_size = int(tile_size if tile_size is not None else self.tile_size)
        img_rgb = image.convert("RGB")
        width, height = img_rgb.size

        # Guard for small canvases: if smaller than tile_size in either dimension,
        # pad canvas with white (standard drawing background) and crop results back.
        if width < actual_tile_size or height < actual_tile_size:
            pad_w = max(width, actual_tile_size)
            pad_h = max(height, actual_tile_size)
            padded_img = Image.new("RGB", (pad_w, pad_h), color=(255, 255, 255))
            padded_img.paste(img_rgb, (0, 0))
            full_mask, full_probs = self.predict_image_sliding_window(
                padded_img,
                tile_size=actual_tile_size,
                overlap=overlap,
            )
            return full_mask[:height, :width], full_probs[:height, :width]

        # If exactly tile size, predict directly
        if width == actual_tile_size and height == actual_tile_size:
            mask = self.predict_tile(img_rgb)
            probs = np.eye(4)[mask].astype(np.float32)
            return mask, probs

        stride = int(actual_tile_size * (1.0 - overlap))
        num_classes = self.config.get("num_classes", 4)

        prob_canvas = np.zeros((height, width, num_classes), dtype=np.float32)
        weight_canvas = np.zeros((height, width), dtype=np.float32)
        hann = self.hann_window if actual_tile_size == self.tile_size else create_hann_window(actual_tile_size)

        y_coords = list(range(0, height - actual_tile_size + 1, stride))
        if len(y_coords) == 0 or y_coords[-1] + actual_tile_size < height:
            y_coords.append(max(0, height - actual_tile_size))

        x_coords = list(range(0, width - actual_tile_size + 1, stride))
        if len(x_coords) == 0 or x_coords[-1] + actual_tile_size < width:
            x_coords.append(max(0, width - actual_tile_size))

        for y in y_coords:
            for x in x_coords:
                crop = img_rgb.crop((x, y, x + actual_tile_size, y + actual_tile_size))
                crop_t = TF.to_tensor(crop)
                crop_t = TF.normalize(crop_t, mean=IMAGENET_MEAN, std=IMAGENET_STD)
                x_tensor = crop_t.unsqueeze(0).to(self.device)

                outputs = self.model(x_tensor)
                logits = outputs.logits if hasattr(outputs, "logits") else (outputs["logits"] if isinstance(outputs, dict) else outputs)
                probs = F.softmax(logits, dim=1).squeeze(0).permute(1, 2, 0).cpu().numpy()

                # Weight by 2D Hann apodization window
                weighted_probs = probs * hann[:, :, np.newaxis]
                prob_canvas[y : y + actual_tile_size, x : x + actual_tile_size] += weighted_probs
                weight_canvas[y : y + actual_tile_size, x : x + actual_tile_size] += hann
```

---

### File 2: `drywall_detection/checkpoints/best_model/config.json`

**Before (lines 8–17)**:
```json
  "input_size": [
    256,
    256
  ],
  "input_resolution": [
    256,
    256
  ],
  "tile_size": 256,
  "tile_overlap": 64,
```
**After**:
```json
  "input_size": [
    512,
    512
  ],
  "input_resolution": [
    512,
    512
  ],
  "tile_size": 512,
  "tile_overlap": 102,
```

---

### File 3: `drywall_detection/models/trainer.py`

**Before (lines 421–423 and 437–441)**:
```python
            "in_channels": 3,
            "input_size": [256, 256],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
```
and
```python
            "input_channels": 3,
            "input_size": [256, 256],
            "input_resolution": [256, 256],
            "tile_size": 256,
            "tile_overlap": 64,
```
**After**:
```python
            "in_channels": 3,
            "input_size": [512, 512],
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
```
and
```python
            "input_channels": 3,
            "input_size": [512, 512],
            "input_resolution": [512, 512],
            "tile_size": 512,
            "tile_overlap": 102,
```

---

### File 4: `drywall_detection/tests/test_models.py`

Append both test cases (`test_infer_cli_invocation` and `test_standalone_inferencer_small_canvas_guard`) to the end of `drywall_detection/tests/test_models.py`.

---

## 4. Verification Instructions for Implementation Worker

The implementation worker must run these 4 verification commands upon applying changes:

1. **Verify Standalone CLI Help**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --help
   ```
   *Expected*: Exit code 0, help text rendered.

2. **Verify Standalone CLI Execution on Real Image**:
   ```powershell
   python drywall_detection/checkpoints/best_model/infer.py --input drywall_detection/data/processed/images/mock_plan_00.png --output test_overlay.png
   ```
   *Expected*: Exit code 0, `test_overlay.png` created, JSON stats printed with `"status": "success"`.
   *Cleanup*: Remove `test_overlay.png`.

3. **Run Model Test Suite (Including 2 New Tests)**:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -k "test_infer_cli_invocation or test_standalone_inferencer" -v
   ```
   *Expected*: All 3 inferencer tests pass (including CLI and small canvas guard).

4. **Run Full Model Test Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_models.py -v
   ```
   *Expected*: 19 passed, 0 failed.

5. **Run Full Regression Suite**:
   ```powershell
   python -m pytest drywall_detection/tests/test_coords.py drywall_detection/tests/test_audit.py drywall_detection/tests/test_data.py drywall_detection/tests/test_vector.py drywall_detection/tests/test_schedule.py -v
   ```
   *Expected*: 115 passed, 0 failed.
