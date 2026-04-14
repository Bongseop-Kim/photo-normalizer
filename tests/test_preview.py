import os
from pathlib import Path

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


def _expected_paths(src, input_dir, output_dir):
    # output_path is always output_dir/_preview.html, so parent == output_dir
    preview_parent = output_dir.resolve()
    try:
        source_rel = src.resolve().relative_to(input_dir.resolve())
    except ValueError:
        source_rel = Path(src.name)
    normalized_path = output_dir.resolve() / source_rel
    normalized_rel = os.path.relpath(normalized_path, preview_parent)
    original_rel = os.path.relpath(src.resolve(), preview_parent)
    return normalized_rel, original_rel


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
    html = output_path.read_text()
    assert "red.jpg" in html
    normalized_rel, original_rel = _expected_paths(
        result.records[0].source_path,
        tmp_path,
        tmp_path / "normalized",
    )
    assert f'src="{normalized_rel}"' in html
    assert f'src="{original_rel}"' in html


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


def test_preview_autoescapes_j2_content(tmp_path):
    src = tmp_path / 'evil<script>.jpg'
    src.touch()
    normalized = tmp_path / "normalized"
    normalized.mkdir()
    (normalized / src.name).touch()
    result = BatchResult(
        config_snapshot={},
        reference={},
        records=[
            ImageRecord(
                source_path=src,
                work_path=normalized / src.name,
                config=NormalizerConfig(),
                measurements={},
                warnings=[],
            )
        ],
    )
    output_path = normalized / "_preview.html"
    render_preview(result, output_path=output_path, input_dir=tmp_path, output_dir=normalized)
    html = output_path.read_text()
    assert "evil&lt;script&gt;.jpg" in html
    assert "evil<script>.jpg" not in html


def test_preview_uses_success_items_for_visual_tabs(tmp_path):
    normalized = tmp_path / "normalized"
    normalized.mkdir()

    ok_src = tmp_path / "ok.jpg"
    ok_src.touch()
    (normalized / "ok.jpg").touch()

    bad_src = tmp_path / "bad.jpg"
    bad_src.touch()

    result = BatchResult(
        config_snapshot={},
        reference={},
        records=[
            ImageRecord(
                source_path=ok_src,
                work_path=normalized / "ok.jpg",
                config=NormalizerConfig(),
                measurements={},
                warnings=[],
            ),
            ImageRecord(
                source_path=bad_src,
                work_path=normalized / "bad.jpg",
                config=NormalizerConfig(),
                measurements={},
                warnings=[],
                error="STEP 1 error: no subject detected",
            ),
        ],
    )
    output_path = normalized / "_preview.html"
    render_preview(result, output_path=output_path, input_dir=tmp_path, output_dir=normalized)
    html = output_path.read_text()

    assert 'id="ba-btn-0"' in html
    assert "ok.jpg" in html
    assert "STEP 1 error: no subject detected" in html
    assert 'src="bad.jpg"' not in html
    assert 'id="ba-before" src="../ok.jpg"' in html
    assert 'id="ba-after" class="ba-after" src="ok.jpg"' in html
