import math
import unittest

from inference_autoscaling_bench.metrics import percentile, summarize
from inference_autoscaling_bench.sim import Run
from tests.helpers import tiny_workload


def make_run(arrival, ttft, events=(), cost=100.0, duration=100.0):
    return Run("p", "tiny", duration, list(arrival), [0.0] * len(ttft), list(ttft), [t + 1 for t in ttft], [], list(events),
               cost, 5, 3)


class PercentileTests(unittest.TestCase):
    def test_it_interpolates_between_ranks(self):
        self.assertEqual(percentile([1, 2, 3, 4], 0.5), 2.5)
        self.assertEqual(percentile([1, 2, 3, 4], 0), 1)
        self.assertEqual(percentile([1, 2, 3, 4], 1), 4)
        self.assertAlmostEqual(percentile([10, 20], 0.95), 19.5)

    def test_one_value_is_every_percentile(self):
        self.assertEqual(percentile([7], 0.99), 7)

    def test_no_values_is_an_error(self):
        with self.assertRaises(ValueError):
            percentile([], 0.5)


class SummaryTests(unittest.TestCase):
    def test_goodput_counts_requests_inside_the_objective(self):
        s = summarize(make_run([1, 2, 3, 4], [0.5, 1.0, 2.0, 2.5]), tiny_workload(slo=2.0))
        self.assertEqual(s["goodput"], 0.75)                     # 2.0 meets a 2.0 s objective, 2.5 does not
        self.assertEqual(s["requests"], 4)

    def test_percentiles_are_in_milliseconds(self):
        s = summarize(make_run([1, 2, 3], [0.1, 0.2, 0.3]), tiny_workload())
        self.assertAlmostEqual(s["ttft_p50_ms"], 200)
        self.assertAlmostEqual(s["latency_p95_s"], 1.29)

    def test_a_window_is_unhealthy_when_its_p95_misses_the_objective(self):
        # window 0 (0-10 s): all good. window 1 (10-20 s): p95 is bad. window 3 (30-40 s): also bad.
        s = summarize(make_run([1, 2, 11, 12, 13, 31], [0.1, 0.2, 0.1, 5.0, 6.0, 9.0]), tiny_workload(slo=2.0))
        self.assertEqual(s["unhealthy_s"], 20.0)

    def test_cost_per_good_request_and_mean_replicas(self):
        s = summarize(make_run([1, 2, 3, 4], [0.5, 0.5, 5, 5], cost=300, duration=100), tiny_workload(slo=2.0))
        self.assertEqual(s["replica_seconds_per_good_request"], 150)
        self.assertEqual(s["mean_replicas"], 3)
        self.assertEqual((s["peak_replicas"], s["max_queue"]), (5, 3))

    def test_no_good_request_has_an_infinite_cost_per_good_request(self):
        s = summarize(make_run([1], [9.0]), tiny_workload(slo=2.0))
        self.assertTrue(math.isinf(s["replica_seconds_per_good_request"]))

    def test_a_scale_up_soon_after_a_scale_down_is_a_flap(self):
        events = [(100.0, -3), (150.0, 2), (400.0, -2), (600.0, 4), (700.0, 1)]
        s = summarize(make_run([1], [0.1], events=events), tiny_workload())
        self.assertEqual((s["scale_ups"], s["scale_downs"]), (3, 2))
        self.assertEqual(s["flaps"], 1)                          # 150 follows 100; 600 is 200 s after 400; 700 is 300 s


if __name__ == "__main__":
    unittest.main()
