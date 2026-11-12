import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from noor_four_corner_cropper import (open_image, output_dimensions, save_corrected,
                                      validate_corners, warp_image)


class FourCornerCropperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="cropper-test-عربي-é-")
        self.root = Path(self.tmp.name)
        self.source = self.root / "ورقة-длинное-имя.png"
        im = Image.new("RGB", (100, 100))
        px = im.load()
        for y in range(100):
            for x in range(100): px[x, y] = (x * 2, y * 2, 40)
        im.save(self.source); im.close()
        self.rect = [(10, 10), (90, 10), (90, 90), (10, 90)]

    def tearDown(self): self.tmp.cleanup()

    def test_rectangle_warp_preserves_expected_crop_and_dimensions(self):
        source = open_image(self.source)
        result = warp_image(source, self.rect)
        try:
            self.assertEqual(result.size, (80, 80))
            # Interior points map to the corresponding source crop coordinates.
            self.assertLessEqual(abs(result.getpixel((20, 20))[0] - source.getpixel((30, 30))[0]), 2)
            self.assertLessEqual(abs(result.getpixel((40, 40))[1] - source.getpixel((50, 50))[1]), 2)
        finally: source.close(); result.close()

    def test_trapezoid_corrects_to_rectangular_output(self):
        quad = [(20, 15), (80, 10), (95, 85), (10, 90)]
        source = open_image(self.source)
        result = warp_image(source, quad)
        try:
            self.assertEqual(result.size, output_dimensions(quad))
            self.assertGreater(result.width, 50)
            self.assertGreater(result.height, 50)
            # Border points in this gradient test vary across all sides; the output is not blank.
            self.assertNotEqual(result.getpixel((result.width//2, 3)), (255, 255, 255))
        finally: source.close(); result.close()

    def test_rejects_wrong_count_nonfinite_out_of_bounds_reversed_and_crossed(self):
        for points in (
            [(0, 0)] * 3,
            [(float('nan'), 0), (90, 10), (90, 90), (10, 90)],
            [(-1, 0), (90, 10), (90, 90), (10, 90)],
            list(reversed(self.rect)),
            [(10, 10), (90, 90), (90, 10), (10, 90)],
            [(10, 10), (11, 10), (11, 11), (10, 11)],
        ):
            with self.subTest(points=points), self.assertRaises(ValueError):
                validate_corners(points, 100, 100)

    def test_output_dimensions_are_average_opposite_edge_lengths(self):
        self.assertEqual(output_dimensions(self.rect), (80, 80))
        self.assertGreater(output_dimensions([(10, 10), (70, 10), (80, 90), (0, 90)])[1], 70)

    def test_saves_new_unicode_path_and_preserves_source(self):
        before = self.source.read_bytes()
        target = self.root / "نتيجة-corrigée.png"
        save_corrected(self.source, target, self.rect)
        with Image.open(target) as output:
            self.assertEqual(output.size, (80, 80))
            self.assertEqual(output.mode, "RGB")
        self.assertEqual(self.source.read_bytes(), before)
        self.assertFalse((self.root / "نتيجة-corrigée.tmp.png").exists())

    def test_prevents_overwrite_and_bad_input_without_partial_output(self):
        with self.assertRaisesRegex(ValueError, "must be a new file"):
            save_corrected(self.source, self.source, self.rect)
        bad = self.root / "broken.png"; bad.write_text("not an image", encoding="utf-8")
        target = self.root / "invalid-output.png"
        with self.assertRaises(ValueError): save_corrected(bad, target, self.rect)
        self.assertFalse(target.exists())
        self.assertFalse((self.root / "invalid-output.tmp.png").exists())

    def test_rejects_unsupported_output_extension(self):
        with self.assertRaisesRegex(ValueError, "ending in PNG"):
            save_corrected(self.source, self.root / "result.pdf", self.rect)


if __name__ == "__main__": unittest.main()
