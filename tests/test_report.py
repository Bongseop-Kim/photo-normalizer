import json

from normalizer.models import BatchResult, ImageRecord, NormalizerConfig
from normalizer.report import build_report_dict, write_report


def _record(tmp_path, name="red.jpg", error=None, warnings=None):
    src = tmp_path / name
    src.touch()
    return ImageRecord(
        source_path=src,
        work_path=src,
        config=NormalizerConfig(),
        measurements={
            "original_profile": "sRGB",
            "profile_converted": False,
            "original_brightness_mean": 238.7,
            "brightness_delta": 6.5,
            "original_angle": 42.1,
            "angle_delta": 1.9,
            "angle_corrected": True,
            "original_bbox": [200, 150, 600, 750],
            "corrected_bbox": [195, 145, 610, 760],
            "crop_applied": [180, 130, 640, 780],
            "resize_scale": 1.12,
        },
        warnings=warnings or [],
        error=error,
    )


def test_report_structure(tmp_path):
    record = _record(tmp_path)
    report = build_report_dict(BatchResult(config_snapshot={}, reference={}, records=[record]))
    assert "config" in report and "reference" in report and "files" in report
    assert "red.jpg" in report["files"]


def test_report_includes_measurements(tmp_path):
    record = _record(tmp_path)
    report = build_report_dict(BatchResult(config_snapshot={}, reference={}, records=[record]))
    assert report["files"]["red.jpg"]["original_brightness_mean"] == 238.7


def test_report_includes_warnings(tmp_path):
    record = _record(tmp_path, warnings=["resize_scale exceeds max"])
    report = build_report_dict(BatchResult(config_snapshot={}, reference={}, records=[record]))
    assert len(report["files"]["red.jpg"]["warnings"]) == 1


def test_report_includes_error(tmp_path):
    record = _record(tmp_path, error="STEP 1 error: no contours")
    report = build_report_dict(BatchResult(config_snapshot={}, reference={}, records=[record]))
    assert report["files"]["red.jpg"]["error"] == "STEP 1 error: no contours"


def test_write_report_creates_json(tmp_path):
    record = _record(tmp_path)
    output_path = tmp_path / "_report.json"
    write_report(BatchResult(config_snapshot={}, reference={}, records=[record]), output_path)
    data = json.loads(output_path.read_text())
    assert "files" in data
