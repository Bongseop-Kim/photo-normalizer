from pathlib import Path

from normalizer.models import BatchResult, ImageRecord, NormalizerConfig


def test_config_defaults():
    config = NormalizerConfig()
    assert config.canvas_width == 1000
    assert config.target_ratio == 0.80
    assert config.angle_tolerance == 2.0
    assert config.dry_run is False


def test_image_record_no_error_by_default(tmp_path):
    src = tmp_path / "red.jpg"
    src.touch()
    record = ImageRecord(
        source_path=src,
        work_path=src,
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )
    assert record.error is None


def test_batch_result(tmp_path):
    src = tmp_path / "a.jpg"
    src.touch()
    record = ImageRecord(
        source_path=src,
        work_path=src,
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )
    batch = BatchResult(config_snapshot={}, reference={}, records=[record])
    assert len(batch.records) == 1
