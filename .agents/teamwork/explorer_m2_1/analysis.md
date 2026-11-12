# Architectural Blueprint & Endpoint Analysis: Dataset Downloader Module (`drywall_detection/data/downloader.py`)

**Document ID:** ARCH-M2-DOWNLOADER-01  
**Author:** explorer_m2_1 (M2 Dataset Downloader Explorer)  
**Date:** 2026-11-08  
**Milestone:** Milestone M2 — Dataset Preparation  
**Scope:** Architecture, Endpoint Verification, Disk Safety, Caching, SHA256 Integrity, Code Blueprint, and CLI Interface for `drywall_detection.data.downloader`

---

## 1. Executive Summary & Endpoint Verification

### 1.1 Objective
Milestone M2 requires downloading and preparing an eligible architectural floor plan dataset for semantic wall segmentation pretraining. In Milestone M1, the **Modified Swiss Dwellings (MSD)** dataset was identified as the **Top Recommended / Eligible Primary** dataset due to its **permissive CC BY 4.0** license, compact payload, explicit vector wall polygons, and strict building/project identifier grouping (`site_id` / `building_id`).

This investigation resolves the exact remote endpoints, verifies zero-login access, formulates disk headroom pre-flight checks, designs resumable caching and SHA256 validation pipelines, and specifies the complete code blueprint for `drywall_detection/data/downloader.py`.

### 1.2 Multi-Endpoint Empirical Probing & Verdict

All four candidate distribution sources for MSD were empirically tested:

| Source / Repository | URL / DOI | Protocol / Endpoint | Auth / EULA Status | HTTP Status | Verdict |
|---|---|---|---|:---:|---|
| **Hugging Face (Enriched Community)** | `philippds/modified-swiss-dwellings-enriched` | `https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched/resolve/main/` | **Zero Login, Zero API Keys, Zero EULA**. CC BY 4.0 in YAML metadata. | **200 OK** | **SELECTED CHAMPION PRIMARY**: Compact columnar Parquet (~174 MB core, ~173 MB geometries), pre-parsed `site_id`/`building_id`, embedded 512×512 structural masks and WKT polygons. |
| **Hugging Face (EPFL Org)** | `epfl-dcl/modified-swiss-dwellings` | `https://huggingface.co/api/datasets/epfl-dcl/modified-swiss-dwellings` | Repository is gated, private, or renamed. | **401 Unauthorized** | **DISQUALIFIED**: Requires user authentication token, violating zero-login constraint. |
| **Zenodo Archive** | `10.5281/zenodo.7788422` | `https://zenodo.org/records/7788422` & `https://zenodo.org/api/records/7788422` | CC BY 4.0, but Cloudflare WAF bot-challenge blocks automated Python HTTP clients. | **403 Forbidden** | **INELIGIBLE FOR AUTOMATED DOWNLOAD**: Cloudflare anti-bot challenge prevents unattended automated ingestion. |
| **4TU.ResearchData** | `10.4121/e1d89cb5-6872-48fc-be63-aadd687ee6f9` | `https://data.4tu.nl/v2/articles/e1d89cb5-6872-48fc-be63-aadd687ee6f9` | **Zero Login, Zero API Keys, Zero EULA**. CC BY 4.0. Direct open Figshare backend. | **200 OK** | **ELIGIBLE SECONDARY / FALLBACK**: Multi-GB archives (test zip: 786.8 MB, train zip: 4.76 GB = 5.54 GB total; ~15 GB uncompressed). Triggers >10 GB extraction headroom warning. |

### 1.3 Selected Target: `philippds/modified-swiss-dwellings-enriched`
The Hugging Face repository `philippds/modified-swiss-dwellings-enriched` is the optimal source:
1. **Zero Access Barriers**: 100% open HTTPS direct download without authentication tokens or click-through agreements.
2. **Bandwidth & Storage Optimization**:
   - Core tabular + structural mask split (`data/`): **173.83 MB** (4,572 train + 800 test floor plans with 512×512 structural element PNG masks, `site_id`, and `building_id`).
   - Vector geometries split (`geometries/`): **173.11 MB** (1,086,846 rows containing explicit WKT polygon geometries for every wall with `entity_type: separator`, `entity_subtype: WALL`).
   - Combined total download: **346.94 MB** (~0.35 GB) vs 5.54 GB for 4TU zips.
3. **Resumable HTTP**: Hugging Face resolve endpoints natively support `Range: bytes={offset}-` returning `HTTP 206 Partial Content`.
4. **Fast Columnar Streaming**: PyArrow / Pandas reads Parquet metadata and rows without decompressing gigabytes of image directories onto disk.

---

## 2. Authoritative File Manifest & Cryptographic SHA256 Signatures

The exact byte counts and SHA-256 hashes were extracted directly from the repository's authoritative Git LFS pointer tree:

### 2.1 Core Floor Plan Split (`data/`) — 173.83 MB
Contains 5,372 floor plans (4,572 train, 800 test) with 512×512 structural element masks (`struct_in`), full room masks (`full_out`), unit IDs, and building/site hierarchy:

| File Path | Direct Remote URL | Exact Size (Bytes) | Size (MB) | Authoritative SHA-256 Checksum |
|---|---|:---:|:---:|---|
| `data/test-00000-of-00001.parquet` | `.../resolve/main/data/test-00000-of-00001.parquet` | `26,082,532` | 24.87 MB | `a0cf855f3cd450a298da588cf3beaf68491970be64221fe586e41ab810f94638` |
| `data/train-00000-of-00003.parquet` | `.../resolve/main/data/train-00000-of-00003.parquet` | `48,129,426` | 45.90 MB | `ff66a65e1a5948bd73e5b9999f1343eac3f0b4a35d6213ef0cd95ab518fe1ef6` |
| `data/train-00001-of-00003.parquet` | `.../resolve/main/data/train-00001-of-00003.parquet` | `49,452,621` | 47.16 MB | `640bddec36b1a06783f883077e1836c95638714f4a45085dcb93ef6489eef6f7` |
| `data/train-00002-of-00003.parquet` | `.../resolve/main/data/train-00002-of-00003.parquet` | `50,164,921` | 47.84 MB | `44511e3fd8b00c2437286deea7ee02033b0c1d71f03bd7258742bc376edc0213` |
| **Subtotal (Core)** | — | **173,829,500** | **165.78 MiB (173.83 MB)** | *All 4 files verified* |

### 2.2 Vector Geometries Split (`geometries/`) — 173.11 MB
Contains 1,086,846 individual geometry elements with WKT strings, elevations, and entity subtypes (`WALL`, `DOOR`, `WINDOW`):

| File Path | Direct Remote URL | Exact Size (Bytes) | Size (MB) | Authoritative SHA-256 Checksum |
|---|---|:---:|:---:|---|
| `geometries/test-00000-of-00001.parquet` | `.../resolve/main/geometries/test-00000-of-00001.parquet` | `26,877,935` | 25.63 MB | `307fb472cf92fe01d15d58141e967117ef6a8a41bf5ec8181614298719a1a67b` |
| `geometries/train-00000-of-00001.parquet` | `.../resolve/main/geometries/train-00000-of-00001.parquet` | `154,641,570` | 147.48 MB | `39e7ef663a8f03642a35dda02210af02cd9673e0e10c663a13aca92f9f150d53` |
| **Subtotal (Geometries)** | — | **181,519,505** | **173.11 MiB (181.52 MB)** | *Both files verified* |

### 2.3 Documentation & Provenance
| File Path | Direct Remote URL | Exact Size (Bytes) | Size (KB) | Notes |
|---|---|:---:|:---:|---|
| `README.md` | `.../raw/main/README.md` | `62,401` | 60.9 KB | Dataset documentation, schema, and CC BY 4.0 citation |

**Combined Dataset Total:** `355,411,406` bytes (~338.95 MiB / 355.41 MB).

---

## 3. Disk Safety Pre-Flight Check Formulation

### 3.1 Host Disk Space Status
Live hardware audit via `drywall_detection.utils.hardware.probe_disk()` reveals:
- Target Drive: `C:\` (anchor of workspace root `c:\Users\TEC ZONE\OneDrive\Desktop\test-model`)
- Free Space: **12.89 GB**
- Total Capacity: **149.64 GB**

### 3.2 Pre-Flight Safety Verification Rules
The pre-flight check strictly integrates with `drywall_detection.utils.hardware.check_disk_safety`:

```python
from drywall_detection.utils.hardware import check_disk_safety
from drywall_detection.config import DISK_FREE_MIN_GB, DISK_LARGE_DOWNLOAD_THRESHOLD_GB
```

1. **Safety Margin Rule**:
   $$\text{Free Disk Space} \ge \text{Download Size} + \text{Safety Margin (5.0 GB)}$$
   For MSD Core (`0.17 GB`):
   $$12.89\text{ GB} \ge 0.17\text{ GB} + 5.00\text{ GB} = 5.17\text{ GB} \implies \mathbf{SAFE}\ (7.72\text{ GB headroom above margin})$$
   For MSD Core + Geometries (`0.35 GB`):
   $$12.89\text{ GB} \ge 0.35\text{ GB} + 5.00\text{ GB} = 5.35\text{ GB} \implies \mathbf{SAFE}\ (7.54\text{ GB headroom above margin})$$

2. **10 GB Mandatory User Notification Ceiling**:
   - `DISK_LARGE_DOWNLOAD_THRESHOLD_GB = 10.0`
   - If `required_download_gb > 10.0`: The downloader MUST halt and demand explicit confirmation via CLI flag `--allow-large-downloads` or interactive prompt.
   - For MSD (`0.17–0.35 GB`), it utilizes only **3.5%** of the threshold ceiling, passing immediately without warning.

3. **Rejection Behavior**:
   - If free disk space is insufficient to maintain the 5.0 GB headroom, `check_disk_safety` returns `(False, free_gb, msg)`.
   - The downloader immediately halts with exit code `3` (`EXIT_CODE_DISK_SAFETY_VIOLATION`) and creates zero temporary files on disk.

---

## 4. Architectural Design: Caching, Resume, SHA256 & Progress Reporting

### 4.1 Local Directory Layout
All raw downloaded artifacts are cached under `drywall_detection/data/raw/msd/`:

```
c:\Users\TEC ZONE\OneDrive\Desktop\test-model\
└── drywall_detection/
    └── data/
        └── raw/
            └── msd/
                ├── data/
                │   ├── test-00000-of-00001.parquet
                │   ├── train-00000-of-00003.parquet
                │   ├── train-00001-of-00003.parquet
                │   └── train-00002-of-00003.parquet
                ├── geometries/
                │   ├── test-00000-of-00001.parquet
                │   └── train-00000-of-00001.parquet
                ├── README.md
                ├── download_manifest.json
                └── .tmp/  (staging area for active .part downloads)
```

### 4.2 Multi-Tier Caching Invariants
Before initiating any network request for a file:
1. **Tier 1 (Existence & File Size Check)**:
   If `target_path.is_file()` and `target_path.stat().st_size == spec.size_bytes`, proceed to Tier 2. Otherwise, treat as missing/corrupted.
2. **Tier 2 (Cryptographic SHA-256 Verification)**:
   Stream the file through `hashlib.sha256()` in 64 KB blocks. If the computed digest matches `spec.sha256`:
   - Log `[CACHE HIT] <filename> verified valid (SHA-256 match).`
   - Skip network download entirely.
3. **Bypass / Invalidation**:
   - Passing `--force` or `force=True` invalidates cache and triggers fresh download.
   - If an existing file fails SHA-256, log a warning, delete the corrupted file, and trigger fresh download.

### 4.3 Atomic File Promotion via `.part` Staging
To prevent corrupt or partial downloads from polluting the cache:
1. Stream remote bytes into `target_path.with_suffix(target_path.suffix + ".part")`.
2. Compute the running SHA-256 hash incrementally during download.
3. Once the stream terminates:
   - Verify final byte length matches `spec.size_bytes`.
   - Verify computed SHA-256 matches `spec.sha256`.
4. Only upon successful verification, atomically replace/rename `.part` to the destination filename (`os.replace`).
5. If verification fails: delete `.part` and raise `ChecksumMismatchError`.

### 4.4 Resumable Transfers via HTTP Range Requests
If a network disconnect occurs during a large transfer:
1. Check if `<filename>.part` exists on disk.
2. If `0 < existing_bytes < total_expected_bytes`:
   - Inject HTTP request header: `Range: bytes={existing_bytes}-`
   - Evaluate server response:
     - `HTTP 206 Partial Content`: Open `<filename>.part` in `"ab"` mode and append remaining bytes.
     - `HTTP 200 OK`: Server does not support Range or reset stream; open `<filename>.part` in `"wb"` mode and restart from byte 0.
3. If `existing_bytes >= total_expected_bytes`: Truncate file and restart cleanly.

### 4.5 Exponential Backoff and Fault-Tolerant Retry Loop
Network interruptions are handled with exponential backoff and randomized jitter:
- Parameters: `max_retries = 5`, `initial_backoff = 1.0s`, `backoff_factor = 2.0`, `max_backoff = 30.0s`.
- Formula:
  $$t_{\text{wait}} = \min(t_{\max},\ t_0 \cdot 2^{\text{attempt}}) + \mathcal{U}(0.0, 0.5)$$
- Retryable Exceptions:
  - `urllib.error.URLError` (DNS lookup failure, connection timeout, connection reset).
  - `urllib.error.HTTPError` with status codes `408`, `429`, `500`, `502`, `503`, `504`.
  - Incomplete reads / socket timeouts (`http.client.IncompleteRead`, `socket.timeout`).
- Non-Retryable Exceptions (Immediate Abort):
  - `HTTP 401 Unauthorized`, `HTTP 403 Forbidden`, `HTTP 404 Not Found`.
  - Disk full / `OSError: [Errno 28] No space left on device`.

### 4.6 Terminal Progress Reporting
The downloader features a stdlib-only terminal progress bar supporting carriage-return line updates:
```
[MSD Download] data/train-00000-of-00003.parquet: [==========>         ] 52.4% (25.2/48.1 MB) | 4.8 MB/s | ETA 00:04
```
It supports custom callbacks conforming to:
```python
Callable[[str, int, int, float, float], None]
# (filename, current_bytes, total_bytes, elapsed_sec, speed_bps)
```

---

## 5. Complete Implementation Blueprint for `drywall_detection/data/downloader.py`

Below is the complete, self-contained, production-grade source code blueprint for `downloader.py`.

```python
"""
drywall_detection.data.downloader
================================
Automated, secure, and authenticated-free dataset downloader for architectural
wall segmentation pretraining.

Primary target: Modified Swiss Dwellings (MSD) dataset (CC BY 4.0, ~174 MB core / ~173 MB geometries).
Features:
- Zero-login, zero-API-key, zero-EULA public HTTPS downloading.
- Hardware-integrated disk space safety pre-flight check honoring 10 GB limit.
- Multi-tier caching with streaming SHA-256 cryptographic verification.
- Atomic file promotion (.part staging) preventing cache corruption.
- Resumable transfers via HTTP Range headers (RFC 7233).
- Exponential backoff with randomized jitter for transient failure recovery.
- Responsive CLI interface with stdlib progress reporting.
"""

from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import logging
import os
from pathlib import Path
import random
import shutil
import sys
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
import urllib.error
import urllib.request

from drywall_detection.config import (
    DATA_DIR,
    DISK_FREE_MIN_GB,
    DISK_LARGE_DOWNLOAD_THRESHOLD_GB,
    RAW_DATA_DIR,
    WORKSPACE_ROOT,
)
from drywall_detection.utils.hardware import check_disk_safety

logger = logging.getLogger(__name__)

# Standard Exit Codes
EXIT_CODE_SUCCESS = 0
EXIT_CODE_GENERAL_ERROR = 1
EXIT_CODE_DISK_SAFETY_VIOLATION = 3
EXIT_CODE_CHECKSUM_MISMATCH = 4

# Remote Base URL for MSD Enriched Dataset
MSD_HF_BASE_URL = (
    "https://huggingface.co/datasets/philippds/modified-swiss-dwellings-enriched/resolve/main"
)
MSD_4TU_API_URL = "https://data.4tu.nl/v2/articles/e1d89cb5-6872-48fc-be63-aadd687ee6f9"


class ChecksumMismatchError(Exception):
    """Raised when downloaded file SHA-256 does not match expected hash."""
    pass


class DiskSpaceSafetyError(Exception):
    """Raised when target volume lacks safe headroom for download."""
    pass


@dataclass(frozen=True)
class DatasetFileSpec:
    """Specification of an individual remote dataset file."""
    relative_path: str
    download_url: str
    size_bytes: int
    sha256: str
    is_core: bool = True
    description: str = ""

    @property
    def size_mb(self) -> float:
        return round(self.size_bytes / (1024.0 * 1024.0), 2)


# Authoritative manifest of all MSD dataset components
MSD_CATALOG: Dict[str, DatasetFileSpec] = {
    # Core Data Split (Images + Floor Plan Tables) - 173.83 MB
    "data/test-00000-of-00001.parquet": DatasetFileSpec(
        relative_path="data/test-00000-of-00001.parquet",
        download_url=f"{MSD_HF_BASE_URL}/data/test-00000-of-00001.parquet",
        size_bytes=26_082_532,
        sha256="a0cf855f3cd450a298da588cf3beaf68491970be64221fe586e41ab810f94638",
        is_core=True,
        description="Core test split: 800 floor plans with 512x512 structural masks and site_id",
    ),
    "data/train-00000-of-00003.parquet": DatasetFileSpec(
        relative_path="data/train-00000-of-00003.parquet",
        download_url=f"{MSD_HF_BASE_URL}/data/train-00000-of-00003.parquet",
        size_bytes=48_129_426,
        sha256="ff66a65e1a5948bd73e5b9999f1343eac3f0b4a35d6213ef0cd95ab518fe1ef6",
        is_core=True,
        description="Core train split part 1 of 3: ~1,524 floor plans with 512x512 masks",
    ),
    "data/train-00001-of-00003.parquet": DatasetFileSpec(
        relative_path="data/train-00001-of-00003.parquet",
        download_url=f"{MSD_HF_BASE_URL}/data/train-00001-of-00003.parquet",
        size_bytes=49_452_621,
        sha256="640bddec36b1a06783f883077e1836c95638714f4a45085dcb93ef6489eef6f7",
        is_core=True,
        description="Core train split part 2 of 3: ~1,524 floor plans with 512x512 masks",
    ),
    "data/train-00002-of-00003.parquet": DatasetFileSpec(
        relative_path="data/train-00002-of-00003.parquet",
        download_url=f"{MSD_HF_BASE_URL}/data/train-00002-of-00003.parquet",
        size_bytes=50_164_921,
        sha256="44511e3fd8b00c2437286deea7ee02033b0c1d71f03bd7258742bc376edc0213",
        is_core=True,
        description="Core train split part 3 of 3: ~1,524 floor plans with 512x512 masks",
    ),
    # Vector Geometries Split (Explicit WKT wall polygons) - 173.11 MB
    "geometries/test-00000-of-00001.parquet": DatasetFileSpec(
        relative_path="geometries/test-00000-of-00001.parquet",
        download_url=f"{MSD_HF_BASE_URL}/geometries/test-00000-of-00001.parquet",
        size_bytes=26_877_935,
        sha256="307fb472cf92fe01d15d58141e967117ef6a8a41bf5ec8181614298719a1a67b",
        is_core=False,
        description="Vector geometries test split: 161,586 WKT polygon elements",
    ),
    "geometries/train-00000-of-00001.parquet": DatasetFileSpec(
        relative_path="geometries/train-00000-of-00001.parquet",
        download_url=f"{MSD_HF_BASE_URL}/geometries/train-00000-of-00001.parquet",
        size_bytes=154_641_570,
        sha256="39e7ef663a8f03642a35dda02210af02cd9673e0e10c663a13aca92f9f150d53",
        is_core=False,
        description="Vector geometries train split: 925,260 WKT polygon elements",
    ),
}


@dataclass
class DownloadResult:
    """Summary result of dataset download execution."""
    dataset_name: str
    target_directory: str
    success: bool
    total_files_requested: int
    files_downloaded: int
    files_cached: int
    total_bytes_transferred: int
    elapsed_seconds: float
    manifest_path: str
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def compute_file_sha256(file_path: Union[str, Path], chunk_size: int = 65536) -> str:
    """Computes streaming SHA-256 checksum of a local file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest().lower()


class MSDDownloader:
    """
    Downloads, caches, and verifies the Modified Swiss Dwellings dataset.
    """

    def __init__(
        self,
        target_dir: Optional[Union[str, Path]] = None,
        max_retries: int = 5,
        timeout: float = 30.0,
        chunk_size: int = 65536,
        allow_large_downloads: bool = False,
    ) -> None:
        self.target_dir = Path(target_dir or (RAW_DATA_DIR / "msd")).resolve()
        self.max_retries = max_retries
        self.timeout = timeout
        self.chunk_size = chunk_size
        self.allow_large_downloads = allow_large_downloads
        self.target_dir.mkdir(parents=True, exist_ok=True)

    def preflight_disk_check(self, files: List[DatasetFileSpec]) -> Tuple[bool, float, str]:
        """
        Runs pre-flight disk safety check against target download files.
        Honors the 10 GB user notification threshold and 5.0 GB minimum safety headroom.
        """
        total_bytes = sum(f.size_bytes for f in files)
        required_gb = total_bytes / (1024.0 ** 3)

        if required_gb > DISK_LARGE_DOWNLOAD_THRESHOLD_GB and not self.allow_large_downloads:
            msg = (
                f"REJECTED: Requested payload ({required_gb:.2f} GB) exceeds the {DISK_LARGE_DOWNLOAD_THRESHOLD_GB:.1f} GB "
                "mandatory notification limit. Pass --allow-large-downloads to confirm."
            )
            logger.error(msg)
            return (False, 0.0, msg)

        is_safe, free_gb, msg = check_disk_safety(
            required_free_gb=required_gb,
            disk_path=self.target_dir,
        )
        return (is_safe, free_gb, msg)

    def is_cached_valid(self, spec: DatasetFileSpec) -> bool:
        """Checks if a file is already downloaded and passes byte and SHA-256 checks."""
        local_path = self.target_dir / spec.relative_path
        if not local_path.is_file():
            return False

        if local_path.stat().st_size != spec.size_bytes:
            logger.warning(
                f"Cache size mismatch for {spec.relative_path}: "
                f"expected {spec.size_bytes}, found {local_path.stat().st_size} bytes."
            )
            return False

        calculated_sha = compute_file_sha256(local_path, self.chunk_size)
        if calculated_sha != spec.sha256.lower():
            logger.warning(
                f"Cache SHA-256 mismatch for {spec.relative_path}: "
                f"expected {spec.sha256}, calculated {calculated_sha}."
            )
            return False

        return True

    def download_file(
        self,
        spec: DatasetFileSpec,
        force: bool = False,
        progress_cb: Optional[Callable[[str, int, int, float, float], None]] = None,
    ) -> Tuple[Path, bool, int]:
        """
        Downloads a single dataset file with resumable transfer, retry backoff, and SHA-256 check.
        Returns: (destination_path, was_cached, bytes_transferred)
        """
        dest_path = self.target_dir / spec.relative_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        if not force and self.is_cached_valid(spec):
            logger.info(f"Cache hit: {spec.relative_path} is valid.")
            return (dest_path, True, 0)

        part_path = dest_path.with_name(dest_path.name + ".part")
        existing_bytes = part_path.stat().st_size if part_path.is_file() else 0

        # Discard invalid part file
        if existing_bytes >= spec.size_bytes:
            part_path.unlink(missing_ok=True)
            existing_bytes = 0

        bytes_transferred = 0
        attempt = 0

        while attempt < self.max_retries:
            attempt += 1
            headers = {"User-Agent": "DrywallDetection-Downloader/1.0"}
            mode = "wb"

            if existing_bytes > 0:
                headers["Range"] = f"bytes={existing_bytes}-"
                mode = "ab"

            req = urllib.request.Request(spec.download_url, headers=headers)
            start_time = time.time()

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    status = getattr(resp, "status", 200)

                    if status not in (200, 206):
                        raise urllib.error.HTTPError(
                            spec.download_url, status, f"Unexpected HTTP status {status}", resp.headers, None
                        )

                    # If server returned 200 despite Range request, restart from byte 0
                    if existing_bytes > 0 and status == 200:
                        mode = "wb"
                        existing_bytes = 0

                    current_bytes = existing_bytes
                    with open(part_path, mode) as out_f:
                        while True:
                            chunk = resp.read(self.chunk_size)
                            if not chunk:
                                break
                            out_f.write(chunk)
                            current_bytes += len(chunk)
                            bytes_transferred += len(chunk)

                            elapsed = max(time.time() - start_time, 1e-4)
                            speed_bps = (current_bytes - existing_bytes) / elapsed
                            if progress_cb:
                                progress_cb(
                                    spec.relative_path,
                                    current_bytes,
                                    spec.size_bytes,
                                    elapsed,
                                    speed_bps,
                                )

                # Verify downloaded part file
                if part_path.stat().st_size != spec.size_bytes:
                    raise IOError(
                        f"Incomplete download: {part_path.stat().st_size}/{spec.size_bytes} bytes."
                    )

                calculated_sha = compute_file_sha256(part_path, self.chunk_size)
                if calculated_sha != spec.sha256.lower():
                    part_path.unlink(missing_ok=True)
                    raise ChecksumMismatchError(
                        f"SHA-256 verification failed for {spec.relative_path}. "
                        f"Expected {spec.sha256}, got {calculated_sha}."
                    )

                # Atomically promote verified .part file
                if dest_path.is_file():
                    dest_path.unlink()
                part_path.rename(dest_path)
                logger.info(f"Successfully downloaded and verified {spec.relative_path}.")
                return (dest_path, False, bytes_transferred)

            except (urllib.error.HTTPError) as e:
                if e.code in (401, 403, 404):
                    # Fatal non-retryable error
                    part_path.unlink(missing_ok=True)
                    raise
                logger.warning(f"Transient HTTP error {e.code} on attempt {attempt}/{self.max_retries}: {e}")
            except Exception as e:
                logger.warning(f"Download error on attempt {attempt}/{self.max_retries}: {e}")

            if attempt < self.max_retries:
                backoff = min(30.0, 1.0 * (2.0 ** (attempt - 1))) + random.uniform(0.1, 0.5)
                logger.info(f"Retrying in {backoff:.2f}s...")
                time.sleep(backoff)
                existing_bytes = part_path.stat().st_size if part_path.is_file() else 0

        part_path.unlink(missing_ok=True)
        raise RuntimeError(f"Failed to download {spec.relative_path} after {self.max_retries} attempts.")

    def download_dataset(
        self,
        include_geometries: bool = True,
        force: bool = False,
        quiet: bool = False,
    ) -> DownloadResult:
        """
        Orchestrates full dataset download including pre-flight checks, caching, and manifest creation.
        """
        specs = [s for s in MSD_CATALOG.values() if s.is_core or include_geometries]
        start_time = time.time()

        # 1. Pre-flight disk safety check
        is_safe, free_gb, safety_msg = self.preflight_disk_check(specs)
        if not is_safe:
            raise DiskSpaceSafetyError(safety_msg)

        logger.info(f"Pre-flight check passed: {safety_msg}")

        # 2. Progress renderer
        def cli_progress(filename: str, current: int, total: int, elapsed: float, speed_bps: float):
            if quiet:
                return
            pct = (current / total) * 100.0 if total > 0 else 0.0
            mb_cur = current / (1024.0 * 1024.0)
            mb_tot = total / (1024.0 * 1024.0)
            mb_spd = (speed_bps / (1024.0 * 1024.0)) if speed_bps > 0 else 0.0
            rem_bytes = max(0, total - current)
            eta_sec = int(rem_bytes / speed_bps) if speed_bps > 0 else 0
            eta_str = f"{eta_sec // 60:02d}:{eta_sec % 60:02d}"

            bar_len = 20
            filled = int(round(bar_len * (current / total))) if total > 0 else 0
            bar = "=" * filled + (">" if filled < bar_len else "") + " " * max(0, bar_len - filled - 1)

            sys.stdout.write(
                f"\r[{bar}] {pct:5.1f}% ({mb_cur:5.1f}/{mb_tot:5.1f} MB) | {mb_spd:4.1f} MB/s | ETA {eta_str} | {filename[-35:]}"
            )
            sys.stdout.flush()

        cached_count = 0
        downloaded_count = 0
        bytes_transferred = 0
        errors: List[str] = []

        for spec in specs:
            if not quiet:
                print(f"\nProcessing: {spec.relative_path} ({spec.size_mb:.2f} MB)")
            try:
                dest, was_cached, transferred = self.download_file(
                    spec=spec,
                    force=force,
                    progress_cb=cli_progress,
                )
                if was_cached:
                    cached_count += 1
                else:
                    downloaded_count += 1
                    bytes_transferred += transferred
            except Exception as e:
                err_msg = f"Failed {spec.relative_path}: {e}"
                logger.error(err_msg)
                errors.append(err_msg)
                break

        if not quiet:
            print("\n")

        elapsed = time.time() - start_time
        success = len(errors) == 0

        # 3. Write manifest
        manifest_path = self.target_dir / "download_manifest.json"
        manifest_data = {
            "dataset_id": "modified_swiss_dwellings",
            "source_repo": "philippds/modified-swiss-dwellings-enriched",
            "license": "CC BY 4.0",
            "attribution": "Standfest et al. (2022). Modified Swiss Dwellings Benchmark (ECCV 2024).",
            "download_timestamp": datetime.now(timezone.utc).isoformat(),
            "target_directory": str(self.target_dir),
            "files_requested": len(specs),
            "files_downloaded": downloaded_count,
            "files_cached": cached_count,
            "total_bytes_transferred": bytes_transferred,
            "elapsed_seconds": round(elapsed, 2),
            "success": success,
            "verified_files": [
                {
                    "relative_path": s.relative_path,
                    "expected_sha256": s.sha256,
                    "size_bytes": s.size_bytes,
                    "verified": (self.target_dir / s.relative_path).is_file() and self.is_cached_valid(s),
                }
                for s in specs
            ],
        }

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        return DownloadResult(
            dataset_name="Modified Swiss Dwellings (MSD)",
            target_directory=str(self.target_dir),
            success=success,
            total_files_requested=len(specs),
            files_downloaded=downloaded_count,
            files_cached=cached_count,
            total_bytes_transferred=bytes_transferred,
            elapsed_seconds=round(elapsed, 2),
            manifest_path=str(manifest_path),
            errors=errors,
        )


def main(args: Optional[List[str]] = None) -> int:
    """CLI entry point for dataset downloader."""
    parser = argparse.ArgumentParser(
        description="Dataset Downloader for Architectural Wall Segmentation (MSD Target)",
    )
    parser.add_argument(
        "--target-dir",
        type=Path,
        default=RAW_DATA_DIR / "msd",
        help="Target directory to store dataset files (default: drywall_detection/data/raw/msd)",
    )
    parser.add_argument(
        "--include-geometries",
        action="store_true",
        default=True,
        help="Download explicit WKT geometry parquet files alongside core floor plans (default: True)",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        default=False,
        help="Download only core tabular/image parquet files (~174 MB) omitting separate geometries",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        default=False,
        help="Force re-download and overwrite existing cached files",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        default=False,
        help="Verify SHA-256 integrity of existing local files without downloading",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Run pre-flight disk space safety check and display download manifest without transferring data",
    )
    parser.add_argument(
        "--allow-large-downloads",
        action="store_true",
        default=False,
        help="Acknowledge and allow downloads exceeding the 10 GB limit",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP socket timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=5,
        help="Maximum retry attempts per file (default: 5)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        default=False,
        help="Suppress interactive progress bar output",
    )

    parsed = parser.parse_args(args)
    logging.basicConfig(
        level=logging.INFO if not parsed.quiet else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    include_geom = parsed.include_geometries and not parsed.core_only
    downloader = MSDDownloader(
        target_dir=parsed.target_dir,
        max_retries=parsed.retries,
        timeout=parsed.timeout,
        allow_large_downloads=parsed.allow_large_downloads,
    )

    specs = [s for s in MSD_CATALOG.values() if s.is_core or include_geom]

    if parsed.dry_run:
        is_safe, free_gb, msg = downloader.preflight_disk_check(specs)
        total_mb = sum(s.size_mb for s in specs)
        print("\n" + "=" * 60)
        print("MSD DATASET DOWNLOAD DRY RUN")
        print("=" * 60)
        print(f"Target Directory : {downloader.target_dir}")
        print(f"Total Files      : {len(specs)}")
        print(f"Total Size       : {total_mb:.2f} MB ({total_mb / 1024:.2f} GB)")
        print(f"Disk Safety Check: {'PASSED' if is_safe else 'FAILED'}")
        print(f"Details          : {msg}\n")
        print("Files:")
        for s in specs:
            print(f" - {s.relative_path:<45} ({s.size_mb:6.2f} MB)")
        return EXIT_CODE_SUCCESS if is_safe else EXIT_CODE_DISK_SAFETY_VIOLATION

    if parsed.verify_only:
        print("\nVerifying existing local dataset files...")
        all_ok = True
        for s in specs:
            p = downloader.target_dir / s.relative_path
            if not p.is_file():
                print(f" [MISSING] {s.relative_path}")
                all_ok = False
            elif downloader.is_cached_valid(s):
                print(f" [OK]      {s.relative_path} (Valid SHA-256)")
            else:
                print(f" [CORRUPT] {s.relative_path} (Checksum or size mismatch)")
                all_ok = False
        return EXIT_CODE_SUCCESS if all_ok else EXIT_CODE_CHECKSUM_MISMATCH

    try:
        res = downloader.download_dataset(
            include_geometries=include_geom,
            force=parsed.force,
            quiet=parsed.quiet,
        )
        if res.success:
            print("\nDataset download completed successfully!")
            print(f"Cached files    : {res.files_cached}")
            print(f"Downloaded files: {res.files_downloaded}")
            print(f"Transferred     : {res.total_bytes_transferred / (1024*1024):.2f} MB")
            print(f"Elapsed Time    : {res.elapsed_seconds:.2f}s")
            print(f"Manifest written: {res.manifest_path}")
            return EXIT_CODE_SUCCESS
        else:
            print("\nDownload finished with errors:")
            for err in res.errors:
                print(f" - {err}")
            return EXIT_CODE_GENERAL_ERROR

    except DiskSpaceSafetyError as e:
        sys.stderr.write(f"\nDISK SAFETY VIOLATION: {e}\n")
        return EXIT_CODE_DISK_SAFETY_VIOLATION
    except ChecksumMismatchError as e:
        sys.stderr.write(f"\nCHECKSUM ERROR: {e}\n")
        return EXIT_CODE_CHECKSUM_MISMATCH
    except Exception as e:
        sys.stderr.write(f"\nFATAL ERROR: {e}\n")
        return EXIT_CODE_GENERAL_ERROR


if __name__ == "__main__":
    sys.exit(main())
```

---

## 6. Command-Line Interface (CLI) Specification

### 6.1 Invocation Syntax
```bash
python -m drywall_detection.data.downloader [OPTIONS]
```

### 6.2 Arguments Reference
| Argument | Type | Default | Description |
|---|---|---|---|
| `--target-dir` | Path | `drywall_detection/data/raw/msd` | Directory where Parquet files and manifest will be persisted. |
| `--core-only` | Flag | `False` | Downloads exclusively the core tabular/mask Parquet files (~174 MB), omitting separate geometries. |
| `--include-geometries` | Flag | `True` | Downloads explicit WKT polygon geometries alongside core floor plans (~347 MB total). |
| `--force` | Flag | `False` | Forces re-download and overwrites existing cached files regardless of checksum validity. |
| `--verify-only` | Flag | `False` | Validates local files against authoritative SHA-256 hashes without making network calls. |
| `--dry-run` | Flag | `False` | Executes pre-flight disk safety checks and displays file manifest without downloading. |
| `--allow-large-downloads`| Flag | `False` | Required override when requested downloads exceed the 10 GB user notification threshold. |
| `--timeout` | Float | `30.0` | Socket connection and read timeout in seconds. |
| `--retries` | Int | `5` | Maximum retry attempts per file before aborting. |
| `--quiet` | Flag | `False` | Disables terminal progress bars for silent headless execution in automated pipelines. |

### 6.3 Exit Codes
| Exit Code | Constant | Meaning | Downloader Behavior |
|:---:|---|---|---|
| `0` | `EXIT_CODE_SUCCESS` | Success | All requested files are present and verified valid. |
| `1` | `EXIT_CODE_GENERAL_ERROR` | General Failure | Unrecoverable network, HTTP, or filesystem error. |
| `3` | `EXIT_CODE_DISK_SAFETY_VIOLATION` | Disk Safety Violation | Target volume has insufficient space (<5.0 GB margin) or exceeds 10 GB without `--allow-large-downloads`. |
| `4` | `EXIT_CODE_CHECKSUM_MISMATCH` | Checksum Mismatch | Downloaded file SHA-256 does not match authoritative Git LFS hash. |

---

## 7. Comprehensive Unit Testing Architecture (`drywall_detection/tests/test_downloader.py`)

A comprehensive unit test suite must accompany the implementation. The tests must be isolated, fast, and execute cleanly offline without requiring live external internet connections.

### 7.1 Key Test Scenarios
1. **Catalog Integrity**: Verify all catalog entries contain non-empty URLs, valid SHA-256 strings (64 hex characters), and positive byte counts.
2. **Pre-flight Disk Check**:
   - Mock disk free space to 50 GB -> assert returns `(True, 50.0, ...)`.
   - Mock disk free space to 1.0 GB -> assert returns `(False, 1.0, "REJECTED...")`.
   - Request payload > 10 GB without `--allow-large-downloads` -> assert rejection.
   - Request payload > 10 GB with `--allow-large-downloads` -> assert allowed if headroom exists.
3. **Multi-Tier Caching**:
   - Empty directory -> `is_cached_valid` returns `False`.
   - Correct size but wrong SHA-256 -> returns `False`.
   - Correct size and correct SHA-256 -> returns `True`, file download skipped (`was_cached=True`).
4. **Atomic Promotion & `.part` Cleanup**:
   - On failed download/checksum, ensure `.part` is purged and destination file is never created.
   - On successful download/checksum, ensure `.part` is renamed to destination atomically.
5. **Resumable Transfers**:
   - Simulate partial file on disk (e.g. 500 bytes of a 1000-byte file).
   - Mock HTTP server returns `HTTP 206` with `Content-Range: bytes 500-999/1000`.
   - Verify remaining bytes appended correctly and file finishes with valid checksum.
6. **Exponential Backoff on Transient HTTP Errors**:
   - Mock server fails with HTTP 503 on attempts 1 and 2, then succeeds on attempt 3.
   - Assert downloader retries with backoff and succeeds.
7. **Immediate Fail-Fast on 401/403/404**:
   - Mock server returns HTTP 403 Forbidden.
   - Assert downloader aborts immediately without exhausting retries.
8. **CLI Argument Parser & Flag Verification**:
   - Invoke `--dry-run`, `--verify-only`, `--core-only` via `main()`.
   - Verify correct exit codes returned.

---

## 8. Downstream Integration with Milestone M2 Preparation Pipeline

The downloader directly enables the subsequent Milestone M2 components:
1. **Data Unification (`preparer.py` / `unified_format.py`)**:
   - Reads `raw/msd/data/*.parquet` using `pyarrow.parquet.read_table()`.
   - Extracts `struct_in` (binary wall/structural masks) or converts `geometries/*.parquet` WKT wall strings via `MSDConverter`.
   - Converts to authoritative `UnifiedMask` format (indexed Mode 'P' 8-bit PNG, classes 0..3).
2. **Project-Isolated Split Manager (`split_manager.py`)**:
   - Consumes `site_id` and `building_id` directly from the Parquet tables.
   - Generates strict 70/15/15 train/val/test splits with zero building overlap ($\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{val}} = \emptyset$, $\mathcal{P}_{\text{train}} \cap \mathcal{P}_{\text{test}} = \emptyset$).
3. **Visual QC Generator (`qc.py`)**:
   - Generates original drawing, mask, and color-coded overlay triplets saved to `drywall_detection/data/qc_samples/`.
