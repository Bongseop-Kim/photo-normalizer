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


def test_pipeline_rejects_same_input_and_output_dir(batch):
    with pytest.raises(ValueError, match="must not be the same"):
        run_pipeline(batch, batch, NormalizerConfig(dry_run=True))


def test_pipeline_rejects_nested_output_dir(batch):
    output_dir = batch / "nested-output"

    with pytest.raises(ValueError, match="must not contain each other"):
        run_pipeline(batch, output_dir, NormalizerConfig(dry_run=True))


def test_pipeline_rejects_non_empty_output_dir(batch, tmp_path):
    output_dir = tmp_path / "norm"
    output_dir.mkdir()
    (output_dir / "stale.jpg").write_bytes(b"stale")

    with pytest.raises(ValueError, match="output_dir must be empty"):
        run_pipeline(batch, output_dir, NormalizerConfig(dry_run=True))


def test_pipeline_redetect_uses_same_detection_parameters(tmp_path, monkeypatch):
    from normalizer import pipeline as pipeline_module

    input_dir = tmp_path / "input"
    input_dir.mkdir()
    make_product_image(input_dir, filename="single.jpg", angle=1.5)
    output_dir = tmp_path / "norm"
    config = NormalizerConfig(
        dry_run=True,
        morphology_enabled=True,
        morphology_kernel_size=7,
        corner_sample_size=42,
    )
    calls: list[dict] = []

    def fake_detect(image_path, **kwargs):
        calls.append(kwargs)
        return ((10, 10, 100, 100), 5.0, 240.0)

    def fake_step0(record):
        return record

    def fake_step2_rotate(record, reference_angle):
        record.measurements["angle_corrected"] = True
        record.measurements["angle_delta"] = 5.0
        return record

    def fake_step3(record, bbox):
        record.measurements["step3_bbox"] = list(bbox)
        return record

    def fake_step4(record, reference_bg):
        return record

    def fake_step5(record, output_path):
        return record

    monkeypatch.setattr(pipeline_module, "detect_subject", fake_detect)
    monkeypatch.setattr(pipeline_module, "step0_color_normalize", fake_step0)
    monkeypatch.setattr(pipeline_module, "step2_rotate", fake_step2_rotate)
    monkeypatch.setattr(pipeline_module, "step3_crop_resize", fake_step3)
    monkeypatch.setattr(pipeline_module, "step4_brightness", fake_step4)
    monkeypatch.setattr(pipeline_module, "step5_finalize", fake_step5)
    monkeypatch.setattr(pipeline_module, "write_report", lambda *args, **kwargs: None)
    monkeypatch.setattr(pipeline_module, "render_preview", lambda *args, **kwargs: None)

    run_pipeline(input_dir, output_dir, config)

    assert len(calls) == 2
    assert calls[0] == calls[1]
