"""The committed results are model runs; these keep the datasets, the report, the chart and the README honest about them."""
import re
import statistics
import unittest
from pathlib import Path

from inference_autoscaling_bench import metrics, report, results, sim, spec, workload
from inference_autoscaling_bench.policies import Bounds

ROOT = Path(__file__).resolve().parent.parent
DATASETS = sorted(p.parent.name for p in (ROOT / "results").glob("*/runs.json") if p.parent.name != "cluster")   # cluster holds cluster runs
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


class ClusterResultsTests(unittest.TestCase):
    DOC = results.read(ROOT / "results" / "cluster")
    CLUSTER_README = (ROOT / "results" / "cluster" / "README.md").read_text()

    @staticmethod
    def goodput(rows, policy, side):
        return statistics.median(r[side]["goodput"] for r in rows if r["policy"] == policy)

    def test_there_are_three_seeds_of_each_of_four_policies(self):
        rows = self.DOC["rows"]
        self.assertEqual(sorted((r["policy"], r["seed"]) for r in rows),
                         sorted((p, s) for p in ("hpa-concurrency", "hpa-queue", "hpa-utilization", "static-24") for s in (1, 2, 3)))

    def test_the_cluster_readme_regenerates_from_the_runs(self):
        from inference_autoscaling_bench import compare
        self.assertEqual(self.CLUSTER_README, compare.markdown(self.DOC))

    def test_the_tail_is_worse_on_the_cluster_in_every_run(self):
        for r in self.DOC["rows"]:
            with self.subTest(policy=r["policy"], seed=r["seed"]):
                self.assertGreater(r["cluster"]["ttft_p95_ms"], r["simulation"]["ttft_p95_ms"])
        self.assertIn("in all 12 runs", FLAT)

    def test_medians_are_within_60_ms(self):
        for policy in ("hpa-concurrency", "hpa-queue", "hpa-utilization", "static-24"):
            if policy == "hpa-utilization":
                continue   # its median first token is 7.7 s on the cluster; the README does not claim agreement for it
            med = lambda side: statistics.median(r[side]["ttft_p50_ms"] for r in self.DOC["rows"] if r["policy"] == policy)
            with self.subTest(policy=policy):
                self.assertLess(abs(med("cluster") - med("simulation")), 60)

    def test_the_scaling_decisions_agree_for_concurrency_and_queue(self):
        for policy in ("hpa-concurrency", "hpa-queue"):
            for r in (r for r in self.DOC["rows"] if r["policy"] == policy):
                self.assertEqual(r["cluster"]["peak_replicas"], r["simulation"]["peak_replicas"])
            med = lambda side: statistics.median(r[side]["scale_ups"] for r in self.DOC["rows"] if r["policy"] == policy)
            self.assertLessEqual(abs(med("cluster") - med("simulation")), 1)

    def test_the_ranking_of_the_signals_differs(self):
        rows = self.DOC["rows"]
        order = lambda side: sorted(("hpa-concurrency", "hpa-queue", "hpa-utilization"), key=lambda p: -self.goodput(rows, p, side))
        self.assertEqual(order("cluster"), ["hpa-concurrency", "hpa-queue", "hpa-utilization"])
        self.assertEqual(order("simulation"), ["hpa-concurrency", "hpa-utilization", "hpa-queue"])
        self.assertIn(f"`hpa-queue` is second ({self.goodput(rows, 'hpa-queue', 'cluster') * 100:.1f}%)", FLAT)
        self.assertIn(f"`hpa-utilization` last ({self.goodput(rows, 'hpa-utilization', 'cluster') * 100:.1f}%", FLAT)

    def test_static_scaling_misses_the_objective_on_the_cluster_only(self):
        self.assertIn(f"serves {self.goodput(self.DOC['rows'], 'static-24', 'cluster') * 100:.1f}% within the objective", FLAT)
        self.assertEqual(self.goodput(self.DOC["rows"], "static-24", "simulation"), 1.0)

    def test_utilization_peaks_below_the_ceiling_on_the_cluster(self):
        peaks = sorted(r["cluster"]["peak_replicas"] for r in self.DOC["rows"] if r["policy"] == "hpa-utilization")
        self.assertEqual((peaks[0], peaks[-1]), (26, 28))


class PodQueueClaimTests(unittest.TestCase):
    """The changelog says per-pod queues move the simulation toward the cluster; this re-runs both and checks it."""
    DOC = results.read(ROOT / "results" / "cluster")
    CHANGELOG = re.sub(r"\s+", " ", (ROOT / "CHANGELOG.md").read_text())

    @classmethod
    def p95(cls, policy, route):
        w = workload.load(ROOT / "workloads" / "burst.json")
        opts = "startup=45" + (",down=300" if policy.startswith("hpa") else "")
        s = spec.parse(f"{policy}:{opts},route={route}")
        vals = []
        for seed in (1, 2, 3):
            run = sim.simulate(workload.generate(w, seed), w, s.make(), s.replica, Policy_bounds(), s.sync_s, s.pod_queues, seed)
            vals.append(metrics.summarize(run, w)["ttft_p95_ms"])
        return statistics.median(vals)

    def test_per_pod_queues_are_between_one_queue_and_the_cluster_for_the_two_policies_quoted(self):
        for policy, central_text, pod_text in (("hpa-concurrency", "45 s", "85 s"), ("static-24", "642 ms", "914 ms")):
            with self.subTest(policy=policy):
                central, pod = self.p95(policy, "central"), self.p95(policy, "pod")
                cluster = statistics.median(r["cluster"]["ttft_p95_ms"] for r in self.DOC["rows"] if r["policy"] == policy)
                self.assertLess(central, pod)
                self.assertLess(pod, cluster)
                fmt = lambda ms: f"{ms / 1000:.0f} s" if ms >= 10000 else f"{ms:,.0f} ms"
                self.assertEqual((fmt(central), fmt(pod)), (central_text, pod_text))
                self.assertIn(central_text, self.CHANGELOG)
                self.assertIn(pod_text, self.CHANGELOG)


def Policy_bounds():
    return Bounds(2, 32)
