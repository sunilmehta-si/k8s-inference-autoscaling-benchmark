import unittest

from inference_autoscaling_bench.forecast import Holt


def fed(values, alpha=0.5, step=15.0, **kwargs):
    holt = Holt(alpha, **kwargs)
    for i, value in enumerate(values):
        holt.update(i * step, value)
    return holt


class LevelTests(unittest.TestCase):
    def test_nothing_observed_forecasts_nothing(self):
        self.assertEqual(Holt().forecast(45), 0.0)

    def test_the_first_observation_is_the_level(self):
        self.assertEqual(fed([7.0]).forecast(0), 7.0)

    def test_a_constant_series_is_forecast_as_itself(self):
        holt = fed([3.0] * 20)
        self.assertAlmostEqual(holt.forecast(0), 3.0)
        self.assertAlmostEqual(holt.forecast(45), 3.0)

    def test_alpha_weighs_the_new_observation_against_the_level(self):
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=0.5).forecast(0), 5.0)
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=0.2).forecast(0), 2.0)
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=1.0).forecast(0), 10.0)


if __name__ == "__main__":
    unittest.main()
