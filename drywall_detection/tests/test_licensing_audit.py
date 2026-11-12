"""
drywall_detection/tests/test_licensing_audit.py
===============================================
Comprehensive unit test suite for dataset licensing audit engine.
Verifies all 7 candidate datasets, DOIs, licensing terms, commercial rights,
access models, report generation, and facade compatibility.
"""

import json
from pathlib import Path
import pytest

from drywall_detection.datasets.licensing_audit import (
    DatasetLicensingAuditor,
    DatasetLicenseInfo,
    AuditStatus,
    CommercialStatus,
    AccessModel,
)
import drywall_detection.audit as audit_module


@pytest.fixture
def auditor() -> DatasetLicensingAuditor:
    return DatasetLicensingAuditor()


def test_registry_completeness(auditor: DatasetLicensingAuditor) -> None:
    """Verifies that exactly 7 candidate datasets are audited in the registry."""
    datasets = auditor.list_all()
    assert len(datasets) == 7

    expected_ids = {
        "modified_swiss_dwellings",
        "cubicasa5k",
        "floorplancad",
        "cvc_fp",
        "r2v",
        "sesyd",
        "archcad_400k",
    }
    actual_ids = {d.dataset_id for d in datasets}
    assert actual_ids == expected_ids


def test_msd_licensing(auditor: DatasetLicensingAuditor) -> None:
    """Verifies Modified Swiss Dwellings (MSD) has CC BY 4.0 and is ELIGIBLE_PRIMARY."""
    msd = auditor.get_dataset("modified_swiss_dwellings")
    assert msd.license_id == "CC-BY-4.0"
    assert msd.commercial_status == CommercialStatus.PERMITTED
    assert msd.commercial_allowed is True
    assert msd.redistribution_allowed is True
    assert msd.attribution_required is True
    assert msd.eligibility_status == AuditStatus.ELIGIBLE_PRIMARY
    assert msd.access_model == AccessModel.DIRECT_OPEN
    assert msd.wall_annotations_available is True
    assert msd.drywall_labels_available is False
    assert "Zenodo" in msd.attribution_text
    assert msd.archive_size_mb <= 200.0


def test_cubicasa_licensing(auditor: DatasetLicensingAuditor) -> None:
    """Verifies CubiCasa5K is CC-BY-NC and ELIGIBLE_BENCHMARK."""
    cb = auditor.get_dataset("cubicasa5k")
    assert "NC" in cb.license_id
    assert cb.commercial_status == CommercialStatus.NON_COMMERCIAL_ONLY
    assert cb.commercial_allowed is False
    assert cb.eligibility_status == AuditStatus.ELIGIBLE_BENCHMARK
    assert cb.wall_annotations_available is True
    assert cb.drywall_labels_available is False
    assert cb.archive_size_mb > 5000.0


def test_disqualified_gated_datasets(auditor: DatasetLicensingAuditor) -> None:
    """Verifies R2V and ArchCAD-400k are disqualified due to access gating."""
    r2v = auditor.get_dataset("r2v")
    assert r2v.eligibility_status == AuditStatus.DISQUALIFIED_GATED
    assert r2v.access_model == AccessModel.GATED_INSTITUTIONAL
    assert r2v.commercial_allowed is False
    assert r2v.wall_annotations_available is False

    archcad = auditor.get_dataset("archcad_400k")
    assert archcad.eligibility_status == AuditStatus.DISQUALIFIED_GATED
    assert archcad.access_model == AccessModel.GATED_MANUAL_REVIEW
    assert archcad.commercial_allowed is False


def test_disqualified_sesyd_no_annotations(auditor: DatasetLicensingAuditor) -> None:
    """Verifies SESYD is disqualified due to zero wall annotations."""
    sesyd = auditor.get_dataset("sesyd")
    assert sesyd.eligibility_status == AuditStatus.DISQUALIFIED_NO_ANNOTATIONS
    assert sesyd.wall_annotations_available is False


def test_cvc_fp_smoke_test(auditor: DatasetLicensingAuditor) -> None:
    """Verifies CVC-FP is ELIGIBLE_SMOKE_TEST with CC BY 4.0."""
    cvc = auditor.get_dataset("cvc_fp")
    assert cvc.eligibility_status == AuditStatus.ELIGIBLE_SMOKE_TEST
    assert cvc.commercial_allowed is True
    assert cvc.wall_annotations_available is True
    assert cvc.archive_size_mb < 500.0


def test_floorplancad_conditional(auditor: DatasetLicensingAuditor) -> None:
    """Verifies FloorPlanCAD is CONDITIONALLY_ELIGIBLE due to third-party disclaimer."""
    fpc = auditor.get_dataset("floorplancad")
    assert fpc.eligibility_status == AuditStatus.CONDITIONALLY_ELIGIBLE
    assert fpc.commercial_status == CommercialStatus.DISCLAIMED_THIRD_PARTY
    assert fpc.commercial_allowed is False


def test_dataset_lookup_aliases(auditor: DatasetLicensingAuditor) -> None:
    """Verifies case-insensitive and alias lookups."""
    assert auditor.get_dataset("msd").dataset_id == "modified_swiss_dwellings"
    assert auditor.get_dataset("CubiCasa").dataset_id == "cubicasa5k"
    assert auditor.get_dataset("archcad").dataset_id == "archcad_400k"
    assert auditor.get_dataset("CVC-FP").dataset_id == "cvc_fp"
    with pytest.raises(KeyError):
        auditor.get_dataset("non_existent_dataset")


def test_json_export(auditor: DatasetLicensingAuditor, tmp_path: Path) -> None:
    """Verifies export_json generates valid JSON matching schema."""
    json_path = tmp_path / "licensing_test.json"
    exported = auditor.export_json(json_path)
    assert exported.is_file()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["audit_version"] == "1.0.0"
    assert "zero_tolerance_rules" in data
    assert data["summary"]["total_audited"] == 7
    assert data["summary"]["eligible_count"] == 4
    assert data["summary"]["disqualified_count"] == 3
    assert data["summary"]["commercial_eligible_count"] == 2
    assert len(data["datasets"]) == 7


def test_markdown_export(auditor: DatasetLicensingAuditor, tmp_path: Path) -> None:
    """Verifies export_markdown produces valid Markdown with all dataset sections."""
    md_path = tmp_path / "licensing_test.md"
    exported = auditor.export_markdown(md_path)
    assert exported.is_file()

    text = md_path.read_text(encoding="utf-8")
    assert "# Candidate Architectural Dataset Licensing & Feasibility Audit Report" in text
    assert "Modified Swiss Dwellings (MSD)" in text
    assert "CubiCasa5K" in text
    assert "FloorPlanCAD" in text
    assert "CVC-FP" in text
    assert "R2V" in text
    assert "SESYD Floorplans" in text
    assert "ArchCAD-400k" in text


def test_connectivity_safe_offline(auditor: DatasetLicensingAuditor) -> None:
    """Verifies verify_connectivity completes safely without unhandled exceptions."""
    results = auditor.verify_connectivity(timeout_seconds=2)
    assert isinstance(results, dict)
    assert len(results) == 7
    for ds_id, status in results.items():
        assert "url" in status
        assert "reachable" in status


def test_audit_facade_alias() -> None:
    """Verifies drywall_detection.audit exports identical classes and aliases."""
    assert audit_module.DatasetLicensingAuditor is DatasetLicensingAuditor
    assert audit_module.AuditStatus is AuditStatus
    assert audit_module.CommercialStatus is CommercialStatus
    assert audit_module.AccessModel is AccessModel
    assert audit_module.DatasetLicenseInfo is DatasetLicenseInfo
    auditor = audit_module.DatasetLicensingAuditor()
    assert len(auditor.list_all()) == 7
    # Also verify original DatasetAuditor is preserved
    assert hasattr(audit_module, "DatasetAuditor")
    orig_auditor = audit_module.DatasetAuditor()
    assert len(orig_auditor.get_candidate_specs()) == 6
