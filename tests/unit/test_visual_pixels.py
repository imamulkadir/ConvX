import numpy as np
from converter.visual_validation.pixels import compare_pixels
from PIL import Image


def test_exact_pixels_are_not_normalized():
    image = Image.new("RGB", (20, 20), "white")
    metrics, heat, _ = compare_pixels(image, image)
    assert metrics["raw_difference_pixels"] == metrics["unexplained_difference_pixels"] == 0
    assert heat.size == image.size


def test_single_pixel_displacement_cannot_be_explained_without_geometry():
    a = np.full((20, 20, 3), 255, dtype=np.uint8)
    a[5:15, 8:10] = 0
    b = np.roll(a, 1, axis=1)
    metrics, _, _ = compare_pixels(
        Image.fromarray(a), Image.fromarray(b), [(0, 0, 20, 20)], structure_equal=False
    )
    assert metrics["raw_difference_pixels"] > 0 and metrics["explained_antialias_pixels"] == 0


def test_neutral_edge_tones_need_exact_structural_evidence():
    a = np.full((20, 20, 3), 255, dtype=np.uint8)
    a[5:15, 8:10] = 0
    a[5:15, 10] = 100
    b = a.copy()
    b[5:15, 10] = 120
    source, actual = Image.fromarray(a), Image.fromarray(b)
    denied, _, _ = compare_pixels(source, actual, [(0, 0, 20, 20)], structure_equal=False)
    proven, _, _ = compare_pixels(source, actual, [(0, 0, 20, 20)], structure_equal=True)
    assert denied["antialias_candidate_pixels"] == 10 and denied["unexplained_difference_pixels"] == 10
    assert proven["explained_antialias_pixels"] == 10 and proven["unexplained_difference_pixels"] == 0


def test_colored_graphic_differences_are_never_antialias_explanations():
    a = Image.new("RGB", (20, 20), "red")
    b = Image.new("RGB", (20, 20), "blue")
    metrics, _, _ = compare_pixels(a, b, [(0, 0, 20, 20)], structure_equal=True)
    assert metrics["unexplained_difference_pixels"] == 400


def test_dimensions_fail_without_resizing():
    metrics, heat, _ = compare_pixels(Image.new("RGB", (2, 2)), Image.new("RGB", (3, 2)))
    assert not metrics["size_equal"] and heat is None
