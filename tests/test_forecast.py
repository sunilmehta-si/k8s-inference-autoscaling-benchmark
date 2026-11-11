import random
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

    def test_a_fall_is_never_forecast_below_nothing(self):
        holt = fed([10.0, 6.0, 2.0, 0.5])
        self.assertLess(holt.trend, 0)
        self.assertEqual(holt.forecast(600), 0.0)

    def test_a_ramp_is_forecast_above_the_latest_observation_and_a_fall_below_it(self):
        self.assertGreater(fed([1.0, 2.0, 3.0, 4.0]).forecast(45), 4.0)
        self.assertLess(fed([4.0, 3.0, 2.0, 1.0]).forecast(45), 1.0)

    def test_beta_weighs_a_change_of_level_against_the_trend_so_far(self):
        # From level 0 to 10 in one 15 s step with alpha 1: the level moved 10/15 per second, and beta of that is kept.
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=1.0, beta=0.3).trend, 0.3 * 10 / 15)
        self.assertAlmostEqual(fed([0.0, 10.0], alpha=1.0, beta=1.0).trend, 10 / 15)
        self.assertEqual(fed([0.0, 10.0], alpha=1.0, beta=0.0).trend, 0.0)


class BehaviourTests(unittest.TestCase):
    """What the default forecaster does with the shapes the workloads have, at the HPA's 15 s sync."""

    def test_the_trend_is_per_second_so_the_sync_period_does_not_change_a_learned_ramp(self):
        slow = fed([3.0 + 0.1 * 15 * i for i in range(40)], step=15.0)
        fast = fed([3.0 + 0.1 * 5 * i for i in range(120)], step=5.0)
        self.assertAlmostEqual(slow.trend, fast.trend, places=6)

    def test_after_a_step_the_forecast_overshoots_then_settles_on_the_new_level(self):
        holt = fed([3.0] * 10 + [20.0] * 30)
        self.assertAlmostEqual(holt.forecast(45), 20.0, places=2)
        overshoot = fed([3.0] * 10 + [20.0] * 3).forecast(45)
        self.assertGreater(overshoot, 20.0)   # the trend learned on the step carries on for a while

    def test_a_step_is_followed_within_a_few_syncs(self):
        holt = fed([3.0] * 10)
        for i in range(4):
            holt.update((10 + i) * 15.0, 20.0)
        self.assertGreater(holt.forecast(0), 17.0)

    def test_noise_around_a_constant_rate_keeps_the_forecast_near_it(self):
        rng = random.Random(7)
        holt = fed([10.0 + rng.uniform(-1.0, 1.0) for _ in range(200)])
        self.assertLess(abs(holt.forecast(45) - 10.0), 3.0)
        self.assertLess(abs(holt.trend), 0.05)


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
