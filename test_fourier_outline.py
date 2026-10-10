import math
import tempfile
import unittest
from pathlib import Path
from fourier_outline import load_points, sample, coefficients, choose, render


class FourierTests(unittest.TestCase):
    def test_circle_one_harmonic(self):
        points = [complex(math.cos(2 * math.pi * i / 128), math.sin(2 * math.pi * i / 128)) for i in range(128)]
        center, terms = coefficients(points, 8)
        selected, error = choose(points, terms, .001)
        self.assertAlmostEqual(abs(center), 0, places=10)
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0][0], 1)
        self.assertLess(error, 1e-7)
        self.assertIn('Epicycles', render(points, center, selected, error))

    def test_uniform_perimeter_and_svg(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'shape.svg'
            path.write_text('<svg xmlns="http://www.w3.org/2000/svg"><polygon points="0,0 4,0 4,4 0,4"/></svg>')
            points = sample(load_points(path), 16)
            self.assertEqual(points[:5], [0j, 1+0j, 2+0j, 3+0j, 4+0j])
            path.write_text('<svg><path d="M 0 0 L 1 1"/></svg>')
            with self.assertRaises(ValueError):
                load_points(path)


if __name__ == '__main__':
    unittest.main()
