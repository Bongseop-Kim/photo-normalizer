import pytest

from normalizer.models import NormalizerConfig
from normalizer.pipeline import run_pipeline
from tests.conftest import make_product_image


@pytest.fixture
def batch(tmp_path):
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    for name, bg, angle in [
        ("red.jpg", 240, 1.5),
        ("blue.jpg", 248, -2.0),
        ("black.jpg", 245, 0.5),
    ]:
        make_product_image(
            input_dir,
            filename=name,
            bg_brightness=bg,
            angle=angle,
            canvas_w=800,
            canvas_h=1000,
            product_color=80 if name != "black.jpg" else 20,
        )
    return input_dir


def test_output_images_created(batch, tmp_path):
    output_dir = tmp_path / "norm"
    run_pipeline(batch, output_dir, NormalizerConfig())
    assert (output_dir / "red.jpg").exists()
    assert (output_dir / "blue.jpg").exists()
    assert (output_dir / "black.jpg").exists()


def test_report_created(batch, tmp_path):
    output_dir = tmp_path / "norm"
    run_pipeline(batch, output_dir, NormalizerConfig())
    assert (output_dir / "_report.json").exists()


def test_preview_created(batch, tmp_path):
    output_dir = tmp_path / "norm"
    run_pipeline(batch, output_dir, NormalizerConfig())
    assert (output_dir / "_preview.html").exists()


def test_dry_run_no_images(batch, tmp_path):
    output_dir = tmp_path / "norm"
    run_pipeline(batch, output_dir, NormalizerConfig(dry_run=True))
    assert not (output_dir / "red.jpg").exists()
    assert (output_dir / "_report.json").exists()
    assert not (output_dir / "_preview.html").exists()


def test_corrupt_file_skipped(batch, tmp_path):
    (batch / "corrupt.jpg").write_bytes(b"not an image")
    output_dir = tmp_path / "norm"
    result = run_pipeline(batch, output_dir, NormalizerConfig())
    assert (output_dir / "red.jpg").exists()
    errors = [record for record in result.records if record.error and record.source_path.name == "corrupt.jpg"]
    assert errors


def test_rotation_redetect_failure_marks_step2_error(batch, tmp_path, monkeypatch):
    from normalizer import pipeline as pipeline_module

    output_dir = tmp_path / "norm"
    original_detect = pipeline_module.detect_subject
    call_count = {"count": 0}

    def fake_detect(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] <= 3:
            return original_detect(*args, **kwargs)
        return None

    def fake_step2_rotate(record, reference_angle):
        record.measurements["angle_corrected"] = True
        record.measurements["angle_delta"] = 1.0
        return record

    monkeypatch.setattr(pipeline_module, "detect_subject", fake_detect)
    monkeypatch.setattr(pipeline_module, "step2_rotate", fake_step2_rotate)

    result = run_pipeline(batch, output_dir, NormalizerConfig())
    assert any(
        record.error and record.error.startswith("STEP 2 error:")
        for record in result.records
    )
