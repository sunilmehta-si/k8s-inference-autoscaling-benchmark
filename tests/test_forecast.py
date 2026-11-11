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


class TrendTests(unittest.TestCase):
    def test_one_observation_has_no_trend(self):
        self.assertEqual(fed([7.0]).trend, 0.0)

    def test_a_linear_ramp_is_learned_and_extrapolated(self):
        # 3 requests per second rising by 0.1 each second: after enough syncs the trend is the slope, and the forecast
        # 45 s ahead is where the ramp will be then.
        holt = fed([3.0 + 0.1 * 15 * i for i in range(40)])
        self.assertAlmostEqual(holt.trend, 0.1, places=6)
        self.assertAlmostEqual(holt.forecast(45), 3.0 + 0.1 * (39 * 15 + 45), places=4)

    def test_a_ramp_is_forecast_above_the_latest_observation_and_a_fall_below_it(self):
        self.assertGreater(fed([1.0, 2.0, 3.0, 4.0]).forecast(45), 4.0)
        self.assertLess(fed([4.0, 3.0, 2.0, 1.0]).forecast(45), 1.0)

    def test_beta_weighs_a_change_of_level_against_the_trend_so_far(self):
        # From level 0 to 10 in one 15 s step with alpha 1: the level moved 10/15 per second, and beta of that is kept.
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=1.0, beta=0.3).trend, 0.3 * 10 / 15)
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=1.0, beta=1.0).trend, 10 / 15)
        self.assertEqual(fed([0.0, 10.0], alpha=1.0, beta=0.0).trend, 0.0)


class ValidationTests(unittest.TestCase):
    def test_alpha_must_be_above_0_and_at_most_1(self):
        for alpha in (0.0, -0.1, 1.5):
            with self.subTest(alpha=alpha), self.assertRaisesRegex(ValueError, "alpha"):
                Holt(alpha)
        Holt(1.0)

    def test_beta_must_be_between_0_and_1(self):
        for beta in (-0.1, 1.01):
            with self.subTest(beta=beta), self.assertRaisesRegex(ValueError, "beta"):
                Holt(0.5, beta)
        Holt(0.5, 0.0), Holt(0.5, 1.0)

    def test_time_must_move_forward(self):
        holt = fed([1.0, 2.0])
        for t in (15.0, 10.0):
            with self.subTest(t=t), self.assertRaisesRegex(ValueError, "forward"):
                holt.update(t, 3.0)

    def test_a_forecast_cannot_look_back(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            fed([1.0]).forecast(-1)


if __name__ == "__main__":
    unittest.main()
