import unittest
import xml.etree.ElementTree as ET

from inference_autoscaling_bench import chart, report


def row(policy, seed, **values):
    base = {"requests": 100, "ttft_p50_ms": 100.0, "ttft_p95_ms": 500.0, "ttft_p99_ms": 900.0, "goodput": 1.0,
            "unhealthy_s": 0.0, "replica_seconds": 1000.0, "replica_seconds_per_good_request": 10.0, "mean_replicas": 4.0,
            "peak_replicas": 6, "max_queue": 3, "scale_ups": 1, "scale_downs": 1, "flaps": 0}
    base.update(values)
    return {"policy": policy, "seed": seed, **base}


def doc(rows, labels=("a", "b")):
    return {
        "title": "A test", "workload": {"name": "w", "duration_s": 120, "slo_ttft_s": 2.0},
        "bounds": {"min_replicas": 2, "max_replicas": 8},
        "policies": [{"label": l, "text": l, "startup_s": 45.0} for l in labels], "runs": rows,
        "demand": [[7.5, 2.0], [22.5, 6.0], [37.5, 4.0]],
        "timelines": {l: [[0.0, 2, 0, 0, 0], [15.0, 2, 3, 10, 40], [30.0, 5, 0, 20, 0]] for l in labels},
    }


class HeldTests(unittest.TestCase):
    def test_better_respects_direction_and_ties(self):
        self.assertEqual(report.better(1, 2, "lower"), 1)
        self.assertEqual(report.better(1, 2, "higher"), -1)
        self.assertEqual(report.better(2, 2, "lower"), 0)

    def test_a_win_in_every_run_is_held(self):
        d = doc([row("a", s, ttft_p95_ms=400.0 + s) for s in (1, 2, 3)] + [row("b", s, ttft_p95_ms=900.0) for s in (1, 2, 3)])
        self.assertEqual(report.held(d, "ttft_p95_ms", "lower"), {"a": ["b"]})

    def test_one_loss_or_one_tie_breaks_it(self):
        lost = doc([row("a", 1, goodput=0.9), row("a", 2, goodput=0.8), row("b", 1, goodput=0.7), row("b", 2, goodput=0.85)])
        self.assertEqual(report.held(lost, "goodput", "higher"), {})
        tied = doc([row("a", 1, goodput=0.9), row("a", 2, goodput=0.8), row("b", 1, goodput=0.9), row("b", 2, goodput=0.5)])
        self.assertEqual(report.held(tied, "goodput", "higher"), {})


class MarkdownTests(unittest.TestCase):
    def setUp(self):
        rows = [row("a", s, ttft_p95_ms=400.0 + s * 10, goodput=0.99, replica_seconds=2000.0) for s in (1, 2, 3)] + \
               [row("b", s, ttft_p95_ms=900.0, goodput=0.90, replica_seconds=1000.0 + s) for s in (1, 2, 3)]
        self.text = report.markdown(doc(rows))

    def test_it_states_the_setup(self):
        self.assertIn("## A test", self.text)
        self.assertIn("2 s", self.text)
        self.assertIn("Each cell is the median of 3 runs", self.text)
        self.assertIn("| `a` | `a` | 2 | 45 s |", self.text)
        self.assertIn("may grow to 8 pods", self.text)

    def test_cells_show_the_median_and_the_range_and_the_best_is_bold(self):
        line = next(l for l in self.text.splitlines() if l.startswith("| TTFT p95"))
        self.assertIn("**420 <sub>(410–430)</sub>**", line)       # a: median of 410, 420, 430
        self.assertIn("| 900 |", line + " ")                      # b: no spread, not bold
        goodput = next(l for l in self.text.splitlines() if l.startswith("| Goodput"))
        self.assertIn("**99.0%**", goodput)
        self.assertNotIn("**90.0%**", goodput)

    def test_the_cheaper_policy_is_bold_on_cost(self):
        line = next(l for l in self.text.splitlines() if l.startswith("| Replica-seconds (cost)"))
        self.assertIn("**1,002 <sub>(1,001–1,003)</sub>**", line)
        self.assertIn("2,000", line)

    def test_unranked_metrics_are_never_bold(self):
        line = next(l for l in self.text.splitlines() if l.startswith("| Mean replicas"))
        self.assertNotIn("**", line)

    def test_the_held_table_lists_who_beat_whom_in_every_run(self):
        self.assertIn("| TTFT p95 (ms) | `a` | `b` |", self.text)
        self.assertIn("| Goodput (TTFT within the objective) | `a` | `b` |", self.text)
        self.assertIn("| Replica-seconds (cost) | `b` | `a` |", self.text)

    def test_when_nothing_held_it_says_so(self):
        rows = [row("a", 1, goodput=0.9), row("a", 2, goodput=0.8), row("b", 1, goodput=0.7), row("b", 2, goodput=0.85)]
        self.assertIn("| none | | |", report.markdown(doc(rows)))

    def test_infinite_cost_shows_as_infinity(self):
        rows = [row("a", 1, replica_seconds_per_good_request=float("inf")), row("b", 1)]
        self.assertIn("∞", report.markdown(doc(rows)))


class ChartTests(unittest.TestCase):
    def test_the_chart_is_valid_svg_naming_every_policy(self):
        text = chart.svg(doc([row("a", 1), row("b", 1)]))
        root = ET.fromstring(text)
        self.assertTrue(root.tag.endswith("svg"))
        self.assertIn(">a<", text)
        self.assertIn(">b<", text)
        self.assertEqual(text.count("<polyline"), 4)       # pods and queue, per policy

    def test_a_static_pool_is_dashed(self):
        d = doc([row("static-4", 1), row("hpa", 1)], labels=("static-4", "hpa"))
        self.assertIn("stroke-dasharray", chart.svg(d))


if __name__ == "__main__":
    unittest.main()
