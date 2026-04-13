from normalizer.models import BatchResult, ImageRecord, NormalizerConfig
from normalizer.preview import render_preview


def _result(tmp_path):
    src = tmp_path / "red.jpg"
    src.touch()
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    (normalized / "red.jpg").touch()
    record = ImageRecord(
        source_path=src,
        work_path=normalized / "red.jpg",
        config=NormalizerConfig(),
        measurements={},
        warnings=[],
    )
    return BatchResult(config_snapshot={}, reference={}, records=[record])


def test_creates_preview_file(tmp_path):
    result = _result(tmp_path)
    output_path = tmp_path / "normalized" / "_preview.html"
    render_preview(
        result,
        output_path=output_path,
        input_dir=tmp_path,
        output_dir=tmp_path / "normalized",
    )
    assert output_path.exists()


def test_preview_contains_filename(tmp_path):
    result = _result(tmp_path)
    output_path = tmp_path / "normalized" / "_preview.html"
    render_preview(
        result,
        output_path=output_path,
        input_dir=tmp_path,
        output_dir=tmp_path / "normalized",
    )
    assert "red.jpg" in output_path.read_text()


def test_preview_has_three_tabs(tmp_path):
    result = _result(tmp_path)
    output_path = tmp_path / "normalized" / "_preview.html"
    render_preview(
        result,
        output_path=output_path,
        input_dir=tmp_path,
        output_dir=tmp_path / "normalized",
    )
    html = output_path.read_text()
    assert html.count("tab-btn") >= 3
