import hashlib
import statistics
import unittest
from pathlib import Path

from inference_autoscaling_bench import workload

ROOT = Path(__file__).resolve().parent.parent


def spec(**changes):
    data = {
        "name": "t", "description": "d", "duration_s": 100, "schedule": [[0, 1], [100, 1]],
        "prompt_tokens": {"median": 100, "sigma": 0.5, "max": 1000},
        "output_tokens": {"median": 50, "sigma": 0.5, "max": 500}, "slo_ttft_s": 2,
    }
    data.update(changes)
    return data


class RateTests(unittest.TestCase):
    def test_the_rate_is_linear_between_points(self):
        w = workload.from_dict(spec(schedule=[[0, 2], [50, 10], [100, 10]]))
        self.assertEqual(w.rate_at(0), 2)
        self.assertEqual(w.rate_at(25), 6)
        self.assertEqual(w.rate_at(50), 10)
        self.assertEqual(w.rate_at(75), 10)
        self.assertEqual(w.rate_at(100), 10)

    def test_the_expected_requests_are_the_area_under_the_schedule(self):
        w = workload.from_dict(spec(schedule=[[0, 2], [50, 10], [100, 10]]))
        self.assertEqual(w.expected_requests, 50 * 6 + 50 * 10)
        self.assertEqual(w.peak_rate, 10)

    def test_bad_schedules_are_refused(self):
        for bad in ([[0, 1]], [[5, 1], [100, 1]], [[0, 1], [60, 1], [50, 1], [100, 1]], [[0, 1], [90, 1]],
                    [[0, -1], [100, 1]], [[0, 0], [100, 0]]):
            with self.subTest(schedule=bad), self.assertRaises(ValueError):
                workload.from_dict(spec(schedule=bad))


class TraceTests(unittest.TestCase):
    def setUp(self):
        self.burst = workload.load(ROOT / "workloads/burst.json")

    def test_a_seed_gives_one_trace_and_another_seed_another(self):
        a = workload.generate(self.burst, 1)
        self.assertEqual(a, workload.generate(self.burst, 1))
        self.assertNotEqual(a, workload.generate(self.burst, 2))

    def test_the_smoke_trace_is_the_same_on_every_python_and_machine(self):
        # If this fails on one Python version only, the random stream changed there and every committed result with it.
        trace = workload.generate(workload.load(ROOT / "workloads/smoke.json"), 1)
        text = "\n".join(f"{r.index},{r.arrival!r},{r.prompt_tokens},{r.output_tokens}" for r in trace)
        self.assertEqual(len(trace), 183)
        self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),
                         "5cf981d4c5b03f92ea29137fa6114fb99ec8a545c2ee11ea86dec9db4471f366")

    def test_arrivals_are_ordered_inside_the_duration_and_indexed_from_zero(self):
        trace = workload.generate(self.burst, 3)
        self.assertEqual([r.index for r in trace], list(range(len(trace))))
        arrivals = [r.arrival for r in trace]
        self.assertEqual(arrivals, sorted(arrivals))
        self.assertTrue(0 < arrivals[0] and arrivals[-1] < self.burst.duration_s)

    def test_sizes_respect_their_caps_and_floor(self):
        for r in workload.generate(self.burst, 4):
            self.assertTrue(1 <= r.prompt_tokens <= self.burst.prompt_max)
            self.assertTrue(1 <= r.output_tokens <= self.burst.output_max)

    def test_the_count_follows_the_schedule_and_the_load_follows_the_spike(self):
        counts = [len(workload.generate(self.burst, s)) for s in range(1, 9)]
        self.assertAlmostEqual(statistics.mean(counts), self.burst.expected_requests, delta=self.burst.expected_requests * 0.03)
        trace = workload.generate(self.burst, 1)
        quiet = sum(1 for r in trace if 700 <= r.arrival < 1100) / 400
        spike = sum(1 for r in trace if 1208 <= r.arrival < 1222) / 14
        self.assertGreater(spike, quiet * 8)


if __name__ == "__main__":
    unittest.main()
