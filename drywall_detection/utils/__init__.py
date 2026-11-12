"""
Utility modules for drywall detection: coordinate transformations and hardware profiling.
"""

__all__ = [
    "pdf_to_pixel",
    "pixel_to_pdf",
    "pdf_bbox_to_pixel",
    "pixel_bbox_to_pdf",
    "transform_bbox_to_pixel",
    "transform_bbox_to_pdf",
    "pdf_geom_to_pixel",
    "pixel_geom_to_pdf",
    "transform_polygon_to_pixel",
    "transform_polygon_to_pdf",
    "pdf_points_to_pixel",
    "pixel_points_to_pdf",
    "get_forward_matrix",
    "get_inverse_matrix",
    "HardwareProfile",
    "TrainingConfig",
    "probe_hardware",
    "auto_configure_training",
    "check_disk_safety",
]


def __getattr__(name: str):
    if name in [
        "pdf_to_pixel",
        "pixel_to_pdf",
        "pdf_bbox_to_pixel",
        "pixel_bbox_to_pdf",
        "transform_bbox_to_pixel",
        "transform_bbox_to_pdf",
        "pdf_geom_to_pixel",
        "pixel_geom_to_pdf",
        "transform_polygon_to_pixel",
        "transform_polygon_to_pdf",
        "pdf_points_to_pixel",
        "pixel_points_to_pdf",
        "get_forward_matrix",
        "get_inverse_matrix",
    ]:
        import drywall_detection.utils.coords as c
        return getattr(c, name)
    elif name in [
        "HardwareProfile",
        "TrainingConfig",
        "probe_hardware",
        "auto_configure_training",
        "check_disk_safety",
    ]:
        import drywall_detection.utils.hardware as h
        return getattr(h, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
