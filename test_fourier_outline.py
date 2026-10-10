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
            path.write_text('<svg><path d="M 0 0 L 4 0 4 4 0 4 Z"/></svg>')
            self.assertEqual(sample(load_points(path), 16), points)

    def test_svg_curves_and_reject_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'shape.svg'
            path.write_text('<svg><path d="M0,0 C10,0 10,10 0,10 S-10,20 -10,10 Q-10,0 0,0 Z"/></svg>')
            points = load_points(path)
            self.assertGreater(len(points), 10)
            self.assertTrue(all(math.isfinite(p.real) and math.isfinite(p.imag) for p in points))
            path.write_text('<svg><path d="M0 0L4 0L4 4L0 4z" transform="scale(2)"/></svg>')
            with self.assertRaisesRegex(ValueError, 'transform'):
                load_points(path)
            path.write_text('<svg><path d="M0 0A4 4 0 0 0 4 4Z"/></svg>')
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                load_points(path)
            path.write_text('<svg><path d="M0 0L4 0Z M10 10L20 10Z"/></svg>')
            with self.assertRaisesRegex(ValueError, 'multiple subpaths'):
                load_points(path)

    def test_rms_prediction_matches_direct_reconstruction(self):
        points = [complex(math.cos(2 * math.pi * j / 64), math.sin(4 * math.pi * j / 64)) for j in range(64)]
        center, terms = coefficients(points, 4)
        selected, error = choose(points, terms, .02)
        direct = sum(abs(p - center - sum(c * complex(math.cos(2 * math.pi * k * j / 64), math.sin(2 * math.pi * k * j / 64)) for k, c in selected)) ** 2 for j, p in enumerate(points)) / 64
        energy = sum(abs(p - center) ** 2 for p in points) / 64
        self.assertAlmostEqual(error, math.sqrt(direct / energy), places=8)

    def test_nonfinite_input_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'bad.csv'
            path.write_text('0,0\n1,0\nnan,1\n')
            with self.assertRaisesRegex(ValueError, 'finite'):
                load_points(path)
            path.write_text('0,0\n1,0\n1,1\n')
            self.assertEqual(len(load_points(path)), 3)
            path.write_text('0,0\n1,0\n0,0\n')
            with self.assertRaises(ValueError):
                load_points(path)

    def test_rounded_output_escapes_script_and_has_slider(self):
        points = [complex(math.cos(2 * math.pi * j / 64), math.sin(2 * math.pi * j / 64)) for j in range(64)]
        center, terms = coefficients(points, 2)
        selected, err = choose(points, terms, .01)
        html = render(points, center, selected, err)
        self.assertIn('input id="count"', html)
        self.assertIn('Export SVG', html)
        self.assertNotIn('/*DATA*/', html)


if __name__ == '__main__':
    unittest.main()
