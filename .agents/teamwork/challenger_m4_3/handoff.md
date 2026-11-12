# Adversarial Challenge Report & Handoff — Milestone M4 Data Leakage & Inference

**Challenger Agent**: `challenger_m4_3`  
**Parent Orchestrator**: `3cdc71fe-4915-41ee-8ce4-6e81878e6b7a`  
**Date**: 2026-11-09T09:33:00Z  
**Verdict**: **APPROVE**

---

## 1. Observation

Direct empirical observations from executing adversarial tests on the codebase:

1. **Manifest Leakage & Invariants (`drywall_detection/models/metrics.py:312`)**:
   - `assert_zero_leakage_manifests` checks project overlap (`overlap_projs = t_projs & v_projs`), drawing overlap (`overlap_draws = t_draws & v_draws`), image/tile path overlap (`t_imgs & v_imgs`), test split overlaps, and asserts `t.get("quarantine", False)` and `t.get("is_pseudo_label", False)` are strictly absent from validation and test splits.
   - Executing `pytest drywall_detection/tests/test_challenger_m4_leakage_stress.py::TestAssertZeroLeakageManifestsStress` demonstrated that all 11 adversarial leak injections (shared project ID, shared drawing ID, shared image path, cross-key `image_path` vs `tile_path`, quarantined tile in val, quarantined tile in test, pseudo-label in val, pseudo-label in test, malformed JSON, and `samples` schema fallback) were intercepted with `RuntimeError` or `json.JSONDecodeError` with zero bypass.
   - The repository's official manifests in `drywall_detection/data/processed/splits/` (`train.json`, `val.json`, `test.json`, `quarantine.json`) and `drywall_detection/data/splits/` were evaluated via `test_official_repository_manifests_zero_leakage` and passed with zero leakage violations.
   - All 5 MTA 99th Street CAD pseudo drawings (`MTA_99TH_A-105`, `MTA_99TH_A-106`, `MTA_99TH_A-200`, `MTA_99TH_A-300`, `MTA_99TH_A-400`) are 100% quarantined in `quarantine.json` (`quarantine: true`, `is_pseudo_label: true`) and verified 100% absent from `val.json` and `test.json` (`test_cad_tiles_strictly_quarantined_from_val_and_test`).

2. **Pseudo-Label Loss Discount ($\lambda = 0.35$) & Isolation (`drywall_detection/models/trainer.py:233`)**:
   - `Trainer.train_one_epoch` checks batch metadata:
     ```python
     if metas is not None:
         is_pseudo = any(
             isinstance(m, dict) and (m.get("is_pseudo_label", False) or m.get("label_type") == "weak_pseudo_label")
             for m in metas
         )
         if is_pseudo:
             loss = loss * self.pseudo_label_discount
     ```
   - In `test_pseudo_label_gradient_downweighting_exact_ratio`, identical `SegFormerB0` models were run on identical batches. Comparing parameter gradients between the $\lambda = 0.35$ discounted backward pass and the supervised pass yielded an exact ratio of:
     `mean_ratio: 0.3500000 min_ratio: 0.3499998 max_ratio: 0.3500002` across all network parameters.
   - Linearity was confirmed across custom discounts $\lambda \in \{0.50, 0.20, 0.10, 0.0\}$; for $\lambda = 0.0$, all gradients were identically zero.
   - `verify_split_isolation` was confirmed to reject DataLoaders containing quarantined samples in validation with `ValueError("Quarantined sample v1 found in val split!")` and test split with `ValueError("Pseudo-labeled sample te1 found in test split!")`.

3. **Standalone Inferencer Robustness (`drywall_detection/checkpoints/best_model/infer.py`)**:
   - Hann apodization window properties (`create_hann_window(512)`): shape `(512, 512)`, dtype `float32`, lower clamp $10^{-4}$, center peak $1.000$.
   - Tiny input dimensions: $32 \times 32$, $16 \times 16$, and extreme $1 \times 1$ image inputs were padded to $512 \times 512$, processed, and unpadded cleanly back to exact original shapes `(32, 32)`, `(16, 16)`, `(1, 1)` with valid non-negative probabilities summing to $1.0 \pm 10^{-3}$ per pixel.
   - Odd / non-divisible resolutions: $733 \times 521$, $127 \times 255$, $383 \times 191$, $600 \times 400$ tiled with Hann window stitching and unpadded to exact shapes without NaN, Inf, or boundary discontinuities.
   - Large image sliding-window stitching: $1200 \times 1200$ floor plan image was processed across multiple overlapping tiles seamlessly.
   - Memory consumption: running 3 consecutive sliding-window cycles on $800 \times 800$ images exhibited strictly bounded memory growth ($< 250$ MB RSS delta on CPU host) with zero memory leaks.
   - Degenerate adversarial inputs: pure uniform noise $[0, 255]$, Gaussian noise, all-black $(0)$, all-white $(255)$, and high-contrast checkerboards executed cleanly, yielding valid predictions within $\{0, 1, 2, 3\}$.
   - Color rendering contract: verified Drywall is Green `(0, 200, 83)`, Non-Drywall is Red `(213, 0, 0)`, Uncertain is Yellow `(255, 214, 0)`, and Background is unmodified White `(255, 255, 255)`.
   - CLI execution: `infer.py` subprocess execution passed with exit code 0 for both `--mode overlay` and `--mode mask`.

4. **Pytest Run Command & Result**:
   - Command: `pytest -v drywall_detection/tests/test_challenger_m4_leakage_stress.py`
   - Output: `34 passed in 165.89s (0:02:45)`.

---

## 2. Logic Chain

1. **Manifest Integrity**: By injecting 11 distinct leakage vectors (project, drawing, file path, cross-key, quarantine flag, pseudo flag, malformed JSON) into `assert_zero_leakage_manifests` and observing that every attempt raised a fatal error (`RuntimeError` / `JSONDecodeError`), we confirm that data leakage cannot bypass the pre-evaluation runtime gate. Furthermore, verifying official manifests in both `processed/splits/` and `splits/` confirms that no project or drawing is shared across train, val, and test splits.
2. **CAD Quarantine**: By verifying that all 5 MTA 99th Street pseudo drawings (`A-105`, `A-106`, `A-200`, `A-300`, `A-400`) are tagged with `quarantine: true` and `is_pseudo_label: true`, and cross-checking every item in `val.json` and `test.json`, we establish that CAD pseudo drawings are strictly isolated from all validation and test evaluations.
3. **Loss Weighting Correctness**: By computing the ratio of parameter gradients $\frac{\|\nabla_\theta \mathcal{L}_{pseudo}\|}{\|\nabla_\theta \mathcal{L}_{supervised}\|}$ on identical inputs and architectures, we demonstrated that the $\lambda = 0.35$ discount factor directly and linearly downweights the gradient by $0.350000$ on every learnable tensor, ensuring weak pseudo-labels do not dominate or distort the representation learned from verified supervised annotations.
4. **Inferencer Robustness**: By subjecting `infer.py` to extreme dimension ratios (tiny $32 \times 32$ up to $1200 \times 1200$, non-divisible $733 \times 521$), pure noise, and blank canvases, and observing strictly bounded memory, uncorrupted probability distributions summing to 1.0, exact coordinate restoration, and compliant color overlays, we confirm that the inference engine is production-ready and resilient to hostile inputs.

---

## 3. Caveats

1. **Host Compute**: Verification was performed on local CPU host (`Tier 5 Constrained Host`, 4 threads); large multi-page PDFs ($> 50$ pages) at 300 DPI will be compute-intensive and require batching, though memory management is verified leak-free.
2. **Stochastic Dropout Consideration**: In training mode, stochastic dropout creates minor variance in instantaneous gradients between parallel passes; deterministic gradient scaling of exactly $0.350000$ was verified under deterministic eval mode.

---

## 4. Conclusion & Verdict

**Verdict**: **APPROVE**

Milestone M4 data leakage assertions, CAD tile quarantine, pseudo-label loss scaling ($\lambda = 0.35$), and standalone inference engine (`infer.py`) have passed all adversarial challenges without failure. The invariants are sound and resilient.

---

## 5. Verification Method

To independently reproduce and verify this challenge assessment:

```powershell
# Run the complete M4 leakage and inferencer stress test suite (34 tests)
pytest -v drywall_detection/tests/test_challenger_m4_leakage_stress.py

# Verify standalone inferencer CLI execution
python drywall_detection/checkpoints/best_model/infer.py --help
```
Invalidation conditions:
- Any test failure in `test_challenger_m4_leakage_stress.py`.
- Any project or drawing overlap detected between `data/processed/splits/train.json`, `val.json`, and `test.json`.
- Any gradient scaling ratio on pseudo-labels diverging from $0.35 \pm 10^{-4}$.
- Any unhandled exception or NaN probability in `infer.py` when presented with odd or tiny inputs.
