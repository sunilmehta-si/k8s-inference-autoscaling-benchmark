"""The committed results are model runs; these keep the datasets, the report, the chart and the README honest about them."""
import re
import statistics
import unittest
from pathlib import Path

from inference_autoscaling_bench import metrics, report, results, sim, spec, workload
from inference_autoscaling_bench.policies import Bounds

ROOT = Path(__file__).resolve().parent.parent
DATASETS = sorted(p.parent.name for p in (ROOT / "results").glob("*/runs.json"))
README = (ROOT / "README.md").read_text()
FLAT = re.sub(r"\s+", " ", README)   # the prose wraps; the checks below read it as one line


def median(dataset: str, policy: str, key: str) -> float:
    doc = results.read(ROOT / "results" / dataset)
    return statistics.median(r[key] for r in doc["runs"] if r["policy"] == policy)


class DatasetTests(unittest.TestCase):
    def test_every_dataset_the_makefile_builds_is_committed_and_the_reverse(self):
        built = re.findall(r"--out results/([\w-]+)", (ROOT / "Makefile").read_text())
        self.assertEqual(sorted(built), DATASETS)
        self.assertEqual(len(DATASETS), 7)

    def test_each_dataset_has_eight_runs_of_every_policy(self):
        for name in DATASETS:
            with self.subTest(dataset=name):
                doc = results.read(ROOT / "results" / name)
                labels = [p["label"] for p in doc["policies"]]
                self.assertEqual(len(labels), len(set(labels)))
                self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["runs"]),
                                 sorted((label, seed) for label in labels for seed in range(1, 9)))

    def test_the_readme_and_chart_of_each_dataset_regenerate_exactly(self):
        for name in DATASETS:
            with self.subTest(dataset=name):
                doc = results.read(ROOT / "results" / name)
                self.assertEqual((ROOT / "results" / name / "README.md").read_text(), report.markdown(doc))
                self.assertEqual((ROOT / "results" / name / "chart.svg").read_text(), __import__("inference_autoscaling_bench.chart", fromlist=["svg"]).svg(doc))

    def test_the_first_run_of_every_policy_is_reproduced_from_its_spec(self):
        # The sample that pins the whole pipeline: a spec, a seed and the workload give the saved numbers again.
        for name in DATASETS:
            doc = results.read(ROOT / "results" / name)
            w = workload.load(ROOT / "workloads" / f"{doc['workload']['name']}.json")
            trace = workload.generate(w, 1)
            for policy in doc["policies"]:
                with self.subTest(dataset=name, policy=policy["label"]):
                    s = spec.parse(policy["text"])
                    bounds = Bounds(policy["min_replicas"], doc["bounds"]["max_replicas"])
                    got = metrics.summarize(sim.simulate(trace, w, s.make(), s.replica, bounds, s.sync_s), w)
                    saved = next(r for r in doc["runs"] if r["policy"] == policy["label"] and r["seed"] == 1)
                    for key, value in got.items():
                        self.assertAlmostEqual(saved[key], value, delta=abs(value) * 1e-9 + 1e-9, msg=key)


class ReadmeTests(unittest.TestCase):
    ROW = re.compile(r"^\| \[[^\]]+\]\(results/([\w-]+)/README\.md\) \| `([^`]+)` \| ([\d.]+)% \| ([\d,]+) \| ([\d,]+) \|$", re.M)

    def test_every_row_of_the_headline_table_is_the_saved_median(self):
        rows = self.ROW.findall(README)
        self.assertGreaterEqual(len(rows), 13)
        for dataset, policy, goodput, cost, unhealthy in rows:
            with self.subTest(dataset=dataset, policy=policy):
                self.assertEqual(goodput, f"{median(dataset, policy, 'goodput') * 100:.1f}")
                self.assertEqual(cost, f"{median(dataset, policy, 'replica_seconds'):,.0f}")
                self.assertEqual(unhealthy, f"{median(dataset, policy, 'unhealthy_s'):,.0f}")

    def test_every_dataset_is_linked(self):
        for name in DATASETS:
            self.assertIn(f"results/{name}/README.md", README)

    def test_the_numbers_in_the_short_answer_are_the_data(self):
        concurrency, static = median("signals", "hpa-concurrency", "goodput"), median("signals", "static-24", "goodput")
        self.assertIn(f"serves {concurrency * 100:.1f}% of requests", FLAT)
        self.assertEqual(static, 1.0)
        self.assertIn(f"costs {median('signals', 'hpa-concurrency', 'replica_seconds') / 43200:.0%} of", FLAT)
        self.assertIn(f"had {median('signals', 'hpa-concurrency', 'flaps'):.0f} flap where queue depth had {median('signals', 'hpa-queue', 'flaps'):.0f}", FLAT)
        points = lambda d, a, b: (median(d, a, "goodput") - median(d, b, "goodput")) * 100  # noqa: E731
        self.assertIn(f"buys {points('targets', 'target-3', 'target-6'):.1f} points of goodput for "
                      f"{median('targets', 'target-3', 'replica_seconds') / median('targets', 'target-6', 'replica_seconds') - 1:.0%} more cost", FLAT)
        self.assertIn(f"buys {points('scale-up-limit', 'limit-none', 'limit-default'):.0f}.", FLAT)
        self.assertIn(f"buy {points('startup', 'startup-10s', 'startup-45s'):.0f}, and deciding every second instead of every 15 buys "
                      f"{points('sync-period', 'sync-1s', 'sync-15s'):.0f}", FLAT)
        self.assertEqual(median("sync-period", "instant", "goodput"), 1.0)
        self.assertIn(f"at {median('sync-period', 'instant', 'replica_seconds') / 43200:.0%} of the static", FLAT)
        self.assertIn(f"to {median('warm-pool', 'min-12', 'goodput') * 100:.1f}% for about "
                      f"{median('warm-pool', 'min-12', 'replica_seconds') / median('warm-pool', 'min-2', 'replica_seconds') - 1:.0%} more", FLAT)
        self.assertIn(f"cuts cost by {1 - median('down-window', 'conc-down-30', 'replica_seconds') / median('down-window', 'conc-down-300', 'replica_seconds'):.0%} "
                      f"and flaps {median('down-window', 'conc-down-30', 'flaps'):.0f} times", FLAT)
        self.assertIn(f"from {median('down-window', 'conc-down-300', 'goodput') * 100:.1f}% to {median('down-window', 'conc-down-30', 'goodput') * 100:.1f}%", FLAT)

    def test_the_claim_that_concurrency_beat_the_others_in_every_run_is_true(self):
        doc = results.read(ROOT / "results/signals")
        beaten = report.held(doc, "goodput", "higher")["hpa-concurrency"]
        for other in ("hpa-utilization", "hpa-queue", "hpa-rps"):
            self.assertIn(other, beaten)

    def test_the_relative_links_resolve(self):
        for target in re.findall(r"\]\(((?:results|docs|workloads)/[^)#]+)", README):
            self.assertTrue((ROOT / target).exists(), target)


if __name__ == "__main__":
    unittest.main()
