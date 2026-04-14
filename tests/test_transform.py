import pytest

from normalizer.transform import compute_brightness_scale, compute_crop_rect


def test_crop_rect_size():
    _, _, size, _, _ = compute_crop_rect(
        bbox=(200, 150, 400, 700),
        canvas_width=1000,
        canvas_height=1000,
        target_ratio=0.80,
        image_width=1200,
        image_height=1400,
    )
    assert abs(size - 875) < 2


def test_crop_rect_centered_on_subject():
    bbox = (500, 150, 400, 700)
    cx, cy, size, _, _ = compute_crop_rect(
        bbox=bbox,
        canvas_width=1000,
        canvas_height=1000,
        target_ratio=0.80,
        image_width=1400,
        image_height=1400,
    )
    subject_cx = bbox[0] + bbox[2] // 2
    subject_cy = bbox[1] + bbox[3] // 2
    crop_cx = cx + size // 2
    crop_cy = cy + size // 2
    assert abs(crop_cx - subject_cx) < 2
    assert abs(crop_cy - subject_cy) < 2


def test_crop_rect_clamps_negative_offsets_to_zero():
    cx, cy, size_w, size_h, _ = compute_crop_rect(
        bbox=(0, 0, 400, 400),
        canvas_width=1000,
        canvas_height=1000,
        target_ratio=0.80,
        image_width=500,
        image_height=500,
    )

    assert (cx, cy) == (0, 0)
    assert (size_w, size_h) == (500, 500)


def test_brightness_scale():
    scale = compute_brightness_scale(image_bg=238.0, reference_bg=245.0)
    assert abs(scale - (245.0 / 238.0)) < 0.001


def test_brightness_scale_equal_returns_one():
    assert compute_brightness_scale(245.0, 245.0) == pytest.approx(1.0)


def test_brightness_scale_zero_denominator():
    assert compute_brightness_scale(0.0, 245.0) == 1.0


def test_crop_rect_clamps_to_image_bounds():
    cx, cy, size_w, size_h, _ = compute_crop_rect(
        bbox=(500, 600, 200, 200),
        canvas_width=1000,
        canvas_height=1000,
        target_ratio=0.80,
        image_width=700,
        image_height=800,
    )

    assert (size_w, size_h) == (250, 250)
    assert (cx, cy) == (450, 550)
    assert cx + size_w == 700
    assert cy + size_h == 800


@pytest.mark.parametrize("bbox", [(10, 20, 0, 50), (10, 20, 50, 0), (10, 20, -5, 50), (10, 20, 50, -5)])
def test_crop_rect_rejects_non_positive_bbox_dimensions(bbox):
    with pytest.raises(ValueError, match="bbox width and height must be > 0"):
        compute_crop_rect(
            bbox=bbox,
            canvas_width=1000,
            canvas_height=1000,
            target_ratio=0.80,
            image_width=1200,
            image_height=1200,
        )


@pytest.mark.parametrize(
    ("canvas_width", "canvas_height"),
    [(0, 1000), (1000, 0), (-1, 1000), (1000, -1)],
)
def test_crop_rect_rejects_non_positive_canvas_dimensions(canvas_width, canvas_height):
    with pytest.raises(ValueError, match="canvas_width and canvas_height must be > 0"):
        compute_crop_rect(
            bbox=(10, 20, 50, 50),
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            target_ratio=0.80,
            image_width=1200,
            image_height=1200,
        )


@pytest.mark.parametrize("target_ratio", [0.0, -0.5, 1.01, float("inf"), float("-inf"), float("nan")])
def test_crop_rect_rejects_out_of_range_target_ratio(target_ratio):
    with pytest.raises(ValueError, match="target_ratio must be > 0 and <= 1.0"):
        compute_crop_rect(
            bbox=(10, 20, 50, 50),
            canvas_width=1000,
            canvas_height=1000,
            target_ratio=target_ratio,
            image_width=1200,
            image_height=1200,
        )
