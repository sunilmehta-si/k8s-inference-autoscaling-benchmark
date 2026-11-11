"""The committed results are model runs; these keep the datasets, the report, the chart and the README honest about them."""
import re
import statistics
import unittest
from pathlib import Path

from inference_autoscaling_bench import compare, metrics, report, results, sim, spec, workload
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
        built = re.findall(r"--out \$\(1\)/([\w-]+)", (ROOT / "Makefile").read_text())
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

    def test_the_ranking_of_the_signals_differs_with_one_queue_and_matches_with_a_queue_per_pod(self):
        rows = self.DOC["rows"]
        order = lambda side: sorted(("hpa-concurrency", "hpa-queue", "hpa-utilization"), key=lambda p: -self.goodput(rows, p, side))
        self.assertEqual(order("cluster"), ["hpa-concurrency", "hpa-queue", "hpa-utilization"])
        self.assertEqual(order("simulation"), ["hpa-concurrency", "hpa-utilization", "hpa-queue"])
        self.assertEqual(order("simulation_pods"), order("cluster"))
        pct = lambda p, side: f"{self.goodput(rows, p, side) * 100:.1f}%"
        for text in (f"`hpa-utilization` second ({pct('hpa-utilization', 'simulation')}) and `hpa-queue` last ({pct('hpa-queue', 'simulation')})",
                     f"`hpa-queue` second ({pct('hpa-queue', 'simulation_pods')}) and `hpa-utilization` last ({pct('hpa-utilization', 'simulation_pods')})",
                     f"on the cluster ({pct('hpa-queue', 'cluster')} and {pct('hpa-utilization', 'cluster')})"):
            self.assertIn(text, FLAT)
        gap = (self.goodput(rows, "hpa-utilization", "simulation_pods") - self.goodput(rows, "hpa-utilization", "cluster")) * 100
        self.assertIn(f"by {gap:.0f} points of goodput against the queue per pod", FLAT)

    def test_a_queue_per_pod_moves_the_tail_toward_the_cluster_and_the_readme_quotes_it(self):
        def p95(policy, side):
            return statistics.median(r[side]["ttft_p95_ms"] for r in self.DOC["rows"] if r["policy"] == policy)
        fmt = lambda ms: f"{ms / 1000:.0f} s" if ms >= 10000 else f"{ms:,.0f} ms"
        for policy in ("hpa-concurrency", "hpa-utilization", "static-24"):
            with self.subTest(policy=policy):
                self.assertLess(p95(policy, "simulation"), p95(policy, "simulation_pods"))
                self.assertLess(p95(policy, "simulation_pods"), p95(policy, "cluster"))
        self.assertGreater(p95("hpa-queue", "simulation_pods"), p95("hpa-queue", "cluster"))   # it overshoots
        for text in (f"from {fmt(p95('hpa-concurrency', 'simulation'))} to {fmt(p95('hpa-concurrency', 'simulation_pods'))} against {fmt(p95('hpa-concurrency', 'cluster'))}",
                     f"from {fmt(p95('hpa-utilization', 'simulation'))} to {fmt(p95('hpa-utilization', 'simulation_pods'))} against {fmt(p95('hpa-utilization', 'cluster'))}",
                     f"from {fmt(p95('static-24', 'simulation'))} to {fmt(p95('static-24', 'simulation_pods'))} against {fmt(p95('static-24', 'cluster'))}",
                     f"{fmt(p95('hpa-queue', 'simulation_pods'))} against {fmt(p95('hpa-queue', 'cluster'))}"):
            self.assertIn(text, FLAT)

    def test_utilization_is_the_one_policy_whose_median_first_token_disagrees(self):
        med = lambda policy, side: statistics.median(r[side]["ttft_p50_ms"] for r in self.DOC["rows"] if r["policy"] == policy)
        self.assertGreater(med("hpa-utilization", "cluster"), 7000)
        self.assertIn(f"{med('hpa-utilization', 'cluster') / 1000:.1f} s on the cluster against {med('hpa-utilization', 'simulation') / 1000:.2f} s", FLAT)

    def test_the_median_peak_of_utilization_with_a_queue_per_pod_is_the_clusters(self):
        peak = lambda side: statistics.median(r[side]["peak_replicas"] for r in self.DOC["rows"] if r["policy"] == "hpa-utilization")
        self.assertEqual((peak("cluster"), peak("simulation_pods"), peak("simulation")), (26, 26, 32))

    def test_static_scaling_misses_the_objective_on_the_cluster_only(self):
        self.assertLess(self.goodput(self.DOC["rows"], "static-24", "cluster"), 1.0)
        self.assertEqual(self.goodput(self.DOC["rows"], "static-24", "simulation"), 1.0)

    def test_utilization_peaks_below_the_ceiling_on_the_cluster_in_every_seed(self):
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


class PodQueueDatasetTests(unittest.TestCase):
    """results/pod-queues is the seven datasets again with a queue per pod; its README quotes them against the originals."""
    README = re.sub(r"\s+", " ", (ROOT / "results" / "pod-queues" / "README.md").read_text())

    def test_it_has_the_same_seven_datasets_with_the_same_policies_and_seeds(self):
        self.assertEqual(sorted(p.parent.name for p in (ROOT / "results" / "pod-queues").glob("*/runs.json")), DATASETS)
        for name in DATASETS:
            with self.subTest(dataset=name):
                a = results.read(ROOT / "results" / name)
                b = results.read(ROOT / "results" / "pod-queues" / name)
                self.assertEqual([p["label"] for p in a["policies"]], [p["label"] for p in b["policies"]])
                self.assertEqual(sorted((r["policy"], r["seed"]) for r in a["runs"]), sorted((r["policy"], r["seed"]) for r in b["runs"]))
                self.assertTrue(all(p["text"].endswith("route=pod") for p in b["policies"]))

    def test_its_readme_and_chart_regenerate_exactly(self):
        from inference_autoscaling_bench import chart
        for name in DATASETS:
            with self.subTest(dataset=name):
                d = ROOT / "results" / "pod-queues" / name
                doc = results.read(d)
                self.assertEqual((d / "README.md").read_text(), report.markdown(doc))
                self.assertEqual((d / "chart.svg").read_text(), chart.svg(doc))

    def test_the_first_run_of_every_policy_is_reproduced_with_a_queue_per_pod(self):
        for name in DATASETS:
            doc = results.read(ROOT / "results" / "pod-queues" / name)
            w = workload.load(ROOT / "workloads" / f"{doc['workload']['name']}.json")
            trace = workload.generate(w, 1)
            for policy in doc["policies"]:
                with self.subTest(dataset=name, policy=policy["label"]):
                    s = spec.parse(policy["text"])
                    self.assertTrue(s.pod_queues)
                    bounds = Bounds(policy["min_replicas"], doc["bounds"]["max_replicas"])
                    got = metrics.summarize(sim.simulate(trace, w, s.make(), s.replica, bounds, s.sync_s, True, 1), w)
                    saved = next(r for r in doc["runs"] if r["policy"] == policy["label"] and r["seed"] == 1)
                    for key, value in got.items():
                        self.assertAlmostEqual(saved[key], value, delta=abs(value) * 1e-9 + 1e-9, msg=key)

    def test_every_row_of_the_readme_table_is_the_saved_median_of_both_datasets(self):
        row = re.compile(r"\| [^|]+ \| `([^`]+)` \| ([\d.]+)% \| ([\d.]+)% \| ([\d,]+) \| ([\d,]+) \|")
        rows = row.findall((ROOT / "results" / "pod-queues" / "README.md").read_text())
        self.assertEqual(len(rows), 10)
        home = {"static-24": "signals", "hpa-concurrency": "signals", "hpa-utilization": "signals", "hpa-queue": "signals", "hpa-rps": "signals",
                "startup-10s": "startup", "limit-none": "scale-up-limit", "min-12": "warm-pool", "conc-down-30": "down-window", "instant": "sync-period"}
        for policy, g1, g2, c1, c2 in rows:
            with self.subTest(policy=policy):
                one, pod = home[policy], f"pod-queues/{home[policy]}"
                self.assertEqual(g1, f"{median(one, policy, 'goodput') * 100:.1f}")
                self.assertEqual(g2, f"{median(pod, policy, 'goodput') * 100:.1f}")
                self.assertEqual(c1, f"{median(one, policy, 'replica_seconds'):,.0f}")
                self.assertEqual(c2, f"{median(pod, policy, 'replica_seconds'):,.0f}")

    def test_the_claims_in_the_prose(self):
        def gain(dataset, a, b):
            return (median(dataset, a, "goodput") - median(dataset, b, "goodput")) * 100
        self.assertIn(f"buy {gain('startup', 'startup-10s', 'startup-45s'):.1f} points of goodput with one queue and {gain('pod-queues/startup', 'startup-10s', 'startup-45s'):.1f} with a queue per pod", self.README)
        self.assertIn(f"buys {gain('scale-up-limit', 'limit-none', 'limit-default'):.1f} and {gain('pod-queues/scale-up-limit', 'limit-none', 'limit-default'):.1f}", self.README)
        self.assertIn(f"costs {median('pod-queues/signals', 'hpa-concurrency', 'replica_seconds') / 43200:.0%} of the static pool, not {median('signals', 'hpa-concurrency', 'replica_seconds') / 43200:.0%}", self.README)
        up = lambda d: (median(d, "min-12", "replica_seconds") / median(d, "min-2", "replica_seconds") - 1) * 100
        self.assertIn(f"lifts goodput by {gain('pod-queues/warm-pool', 'min-12', 'min-2'):.1f} points for {up('pod-queues/warm-pool'):.1f}% more", self.README)
        self.assertIn(f"it lifted it by {gain('warm-pool', 'min-12', 'min-2'):.1f} points for {up('warm-pool'):.1f}%", self.README)
        cut = lambda d: (1 - median(d, "conc-down-30", "replica_seconds") / median(d, "conc-down-300", "replica_seconds")) * 100
        self.assertIn(f"cuts cost by {cut('pod-queues/down-window'):.0f}%, not {cut('down-window'):.0f}%", self.README)
        self.assertIn(f"serve {median('pod-queues/sync-period', 'instant', 'goodput') * 100:.1f}%", self.README)
        self.assertIn(f"static pool of 24 serves {median('pod-queues/signals', 'static-24', 'goodput') * 100:.1f}%", self.README)

    def test_the_win_counts_in_the_prose(self):
        def wins(prefix, other):
            doc = results.read(ROOT / "results" / prefix / "signals") if prefix else results.read(ROOT / "results" / "signals")
            g = {(r["policy"], r["seed"]): r["goodput"] for r in doc["runs"]}
            return sum(g[("hpa-concurrency", s)] > g[(other, s)] for s in range(1, 9))
        self.assertEqual([wins("", o) for o in ("hpa-queue", "hpa-utilization", "hpa-rps")], [8, 8, 8])
        self.assertEqual([wins("pod-queues", o) for o in ("hpa-queue", "hpa-utilization", "hpa-rps")], [5, 8, 8])
        self.assertIn("wins five of eight", self.README)
        self.assertIn("beat slot utilization and request rate in all eight runs", self.README)
        for prefix in ("", "pod-queues"):
            doc = results.read(ROOT / "results" / prefix / "startup") if prefix else results.read(ROOT / "results" / "startup")
            g = {(r["policy"], r["seed"]): r["goodput"] for r in doc["runs"]}
            self.assertTrue(all(g[("startup-10s", s)] > g[("startup-45s", s)] for s in range(1, 9)))


class MetricsLagClaimTests(unittest.TestCase):
    """The README's metrics-lag bullet, number by number."""

    DOC = results.read(ROOT / "results" / "cluster")
    README = (ROOT / "README.md").read_text()
    HPA = ("hpa-concurrency", "hpa-queue", "hpa-utilization")

    def med(self, policy, model, key):
        return statistics.median(r[model][key] for r in self.DOC["rows"] if r["policy"] == policy)

    def test_goodput_with_the_lag_is_within_the_quoted_points_for_every_hpa_policy(self):
        gaps = [abs(self.med(p, "simulation_lag", "goodput") - self.med(p, "cluster", "goodput")) * 100 for p in self.HPA]
        self.assertLessEqual(max(gaps), 3.2 + 0.05)
        self.assertGreater(max(gaps), 3.1)   # "within 3.2 points" is the largest gap, not a loose bound
        for p in self.HPA:
            with self.subTest(policy=p):
                quoted = f"`{p}` {self.med(p, 'simulation_lag', 'goodput') * 100:.1f}% against {self.med(p, 'cluster', 'goodput') * 100:.1f}%"
                self.assertIn(quoted, " ".join(self.README.split()))

    def test_the_concurrency_tail_matches_and_the_utilization_tail_is_shorter(self):
        s = lambda p, m: round(self.med(p, m, "ttft_p95_ms") / 1000)
        self.assertEqual(s("hpa-concurrency", "simulation_lag"), s("hpa-concurrency", "cluster"))
        self.assertIn(f"`hpa-concurrency` is {s('hpa-concurrency', 'cluster')} s on both", " ".join(self.README.split()))
        self.assertLess(s("hpa-utilization", "simulation_lag"), s("hpa-utilization", "cluster"))
        self.assertIn(f"({s('hpa-utilization', 'simulation_lag')} s against {s('hpa-utilization', 'cluster')} s)", " ".join(self.README.split()))

    def test_15_and_45_seconds_fit_goodput_less_well_for_concurrency_and_utilization(self):
        from inference_autoscaling_bench import compare, workload
        burst = workload.load(ROOT / "workloads/burst.json")
        for policy in ("hpa-concurrency", "hpa-utilization"):
            rows = [r for r in self.DOC["rows"] if r["policy"] == policy]
            cluster = statistics.median(r["cluster"]["goodput"] for r in rows)
            def gap(lag):
                return abs(statistics.median(
                    compare.simulate_like({"config": r["config"], "summary": {"policy": policy, "seed": r["seed"]}}, burst,
                                          pod_queues=True, lag_s=lag)["goodput"] for r in rows) - cluster)
            with self.subTest(policy=policy):
                self.assertLess(gap(30), gap(15))
                self.assertLess(gap(30), gap(45))

    def test_static_24_is_untouched_by_the_lag_and_its_gap_is_quoted(self):
        rows = [r for r in self.DOC["rows"] if r["policy"] == "static-24"]
        for r in rows:
            self.assertEqual(r["simulation_lag"], r["simulation_pods"])
        gap = self.med("static-24", "cluster", "ttft_p95_ms") - self.med("static-24", "simulation_lag", "ttft_p95_ms")
        self.assertIn(f"remaining {gap:.0f} ms", self.README)


class UtilizationTailTests(unittest.TestCase):
    """The README's utilization-tail bullet, number by number."""

    DOC = results.read(ROOT / "results" / "cluster")
    README = " ".join((ROOT / "README.md").read_text().split())

    def rows(self, policy):
        return [r for r in self.DOC["rows"] if r["policy"] == policy]

    def model_p95(self, policy, lag):
        from inference_autoscaling_bench import compare
        burst = workload.load(ROOT / "workloads/burst.json")
        return statistics.median(
            compare.simulate_like({"config": r["config"], "summary": {"policy": policy, "seed": r["seed"]}}, burst,
                                  pod_queues=True, lag_s=lag)["ttft_p95_ms"] for r in self.rows(policy)) / 1000

    def test_utilization_caps_a_step_and_concurrency_does_not(self):
        from inference_autoscaling_bench.policies import Hpa, Observation
        flooded = Observation(now=0.0, ready=10, pending=0, running=80, queued=10_000, slots=8, arrival_rate=50.0)
        utilization = Hpa("utilization").decide(flooded, Bounds(2, 32))
        self.assertEqual(utilization, 17)   # ceil(10 / 0.6): every slot busy is the most the signal can say
        self.assertGreater(Hpa("concurrency").decide(flooded, Bounds(2, 32)), utilization)

    def test_15_seconds_more_lag_costs_utilization_four_times_what_it_costs_concurrency(self):
        util = (self.model_p95("hpa-utilization", 30), self.model_p95("hpa-utilization", 45))
        conc = (self.model_p95("hpa-concurrency", 30), self.model_p95("hpa-concurrency", 45))
        self.assertEqual((round(util[1] - util[0]), round(conc[1] - conc[0])), (36, 9))
        self.assertGreater(util[1] - util[0], 3.9 * (conc[1] - conc[0]))
        cluster = statistics.median(r["cluster"]["ttft_p95_ms"] for r in self.rows("hpa-utilization")) / 1000
        self.assertLess(abs(cluster - util[1]), abs(cluster - util[0]))   # the tail sits at 45 s
        self.assertIn(f"by 36 s ({round(util[0])} s to {round(util[1])} s, against {round(cluster)} s on the cluster)"
                      f" and of `hpa-concurrency` by 9 s", self.README)

    def test_most_of_the_gap_is_one_seed(self):
        rows = {r["seed"]: r for r in self.rows("hpa-utilization")}
        gap = {s: round((r["cluster"]["ttft_p95_ms"] - r["simulation_lag"]["ttft_p95_ms"]) / 1000) for s, r in rows.items()}
        self.assertEqual(gap[1], 78)
        self.assertEqual(max(gap[2], gap[3]), 31)
        self.assertEqual((rows[1]["cluster"]["max_queue"], rows[1]["simulation_lag"]["max_queue"]), (1756, 1313))
        self.assertIn("the queue peaked at 1,756 requests on the cluster against 1,313 in the model, 78 s more", self.README)
        self.assertIn("seeds 2 and 3 are within 31 s", self.README)


class ClusterRampTests(unittest.TestCase):
    """results/cluster-ramps: the four ramps on the cluster; the README's cluster-ramp bullets, number by number."""

    RAMPS = (30, 120, 300, 600)
    DOCS = {r: results.read(ROOT / "results" / "cluster-ramps" / f"ramp-{r}") for r in RAMPS}
    README = " ".join((ROOT / "README.md").read_text().split())
    POLICIES = ("hpa-concurrency", "hpa-utilization", "static-24")

    def rows(self, ramp, policy):
        return sorted((r for r in self.DOCS[ramp]["rows"] if r["policy"] == policy), key=lambda r: r["seed"])

    def med(self, ramp, policy, side, key="goodput"):
        return statistics.median(r[side][key] for r in self.rows(ramp, policy))

    def series(self, policy, side):
        return [self.med(r, policy, side) * 100 for r in self.RAMPS]

    @staticmethod
    def quoted(values):
        return ", ".join(f"{v:.1f}%" for v in values[:-1]) + f" and {values[-1]:.1f}%"

    def test_three_seeds_of_three_policies_on_each_ramp_and_the_readmes_regenerate(self):
        from inference_autoscaling_bench import compare
        for ramp, doc in self.DOCS.items():
            with self.subTest(ramp=ramp):
                self.assertEqual(doc["workload"]["name"], f"ramp-{ramp}")
                self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["rows"]),
                                 sorted((p, s) for p in self.POLICIES for s in (1, 2, 3)))
                self.assertEqual((ROOT / "results" / "cluster-ramps" / f"ramp-{ramp}" / "README.md").read_text(), compare.markdown(doc))

    def test_no_ramp_is_slow_enough_on_the_cluster_and_the_lagged_model_said_so(self):
        cluster, one, lag = (self.series("hpa-concurrency", side) for side in ("cluster", "simulation", "simulation_lag"))
        self.assertIn(f"`hpa-concurrency` serves {self.quoted(cluster)} of requests in time on the four ramps", self.README)
        self.assertIn(f"below the one-queue model ({', '.join(f'{v:.1f}%' for v in one)}) in every run", self.README)
        self.assertIn(f"the 30 s lag says {self.quoted(lag)}", self.README)
        best = max(r["cluster"]["goodput"] * 100 for ramp in self.RAMPS for r in self.rows(ramp, "hpa-concurrency"))
        self.assertIn(f"no run serves more than {best:.1f}%", self.README)
        gaps, med_gaps = [], []
        for ramp in self.RAMPS:
            rows = self.rows(ramp, "hpa-concurrency")
            for r in rows:
                with self.subTest(ramp=ramp, seed=r["seed"]):
                    self.assertLess(r["cluster"]["goodput"], min(x["simulation"]["goodput"] for x in rows))
                gaps.append(abs(r["cluster"]["goodput"] - r["simulation_lag"]["goodput"]) * 100)
            med_gaps.append(abs(self.med(ramp, "hpa-concurrency", "cluster") - self.med(ramp, "hpa-concurrency", "simulation_lag")) * 100)
        self.assertIn(f"within {max(gaps):.1f} points of the cluster on every seed of every ramp and within {max(med_gaps):.1f} points on the medians", self.README)

    def test_the_clusters_gain_from_a_longer_ramp_stops_at_300_s(self):
        cluster, one, lag = (self.series("hpa-concurrency", side) for side in ("cluster", "simulation", "simulation_lag"))
        self.assertLess(abs(cluster[3] - cluster[2]), 0.5)
        self.assertGreater(one[3] - one[2], 4)
        self.assertGreater(cluster[2] - cluster[1], 5)   # the gain up to 300 s is real
        self.assertIn(f"moves from {cluster[2]:.1f}% to {cluster[3]:.1f}%, while the one-queue model moves from {one[2]:.1f}% to {one[3]:.1f}%; "
                      f"the lagged model moves from {lag[2]:.1f}% to {lag[3]:.1f}%", self.README)

    def test_the_best_signal_depends_on_the_ramp_and_the_flip_comes_later_than_the_one_queue_model_says(self):
        for ramp in self.RAMPS:
            for u, c in zip(self.rows(ramp, "hpa-utilization"), self.rows(ramp, "hpa-concurrency")):
                with self.subTest(ramp=ramp, seed=u["seed"]):
                    self.assertEqual(u["cluster"]["goodput"] > c["cluster"]["goodput"], ramp == 600)
                    self.assertGreaterEqual(u["simulation"]["goodput"] >= c["simulation"]["goodput"], ramp >= 300)   # one queue: ahead from 300 s
                    self.assertEqual(u["simulation_lag"]["goodput"] > c["simulation_lag"]["goodput"], False)        # lagged: never ahead
        u, c = self.series("hpa-utilization", "cluster"), self.series("hpa-concurrency", "cluster")
        self.assertIn(f"({u[0]:.1f}%, {u[1]:.1f}% and {u[2]:.1f}% against {c[0]:.1f}%, {c[1]:.1f}% and {c[2]:.1f}%)", self.README)
        self.assertIn(f"above it on the 600 s ramp ({u[3]:.1f}% against {c[3]:.1f}%", self.README)
        tails = (self.med(600, "hpa-utilization", "cluster", "ttft_p95_ms") / 1000, self.med(600, "hpa-concurrency", "cluster", "ttft_p95_ms") / 1000)
        self.assertLess(tails[0], tails[1])
        self.assertIn(f"{tails[0]:.1f} s against {tails[1]:.1f} s at the 95th percentile", self.README)
        shares = [x["cluster"]["replica_seconds"] / s["cluster"]["replica_seconds"] * 100
                  for x, s in zip(self.rows(600, "hpa-utilization"), self.rows(600, "static-24"))]
        self.assertIn(f"at {min(shares):.0f}–{max(shares):.0f}% of `static-24`'s cost", self.README)
        lag_u, lag_c = self.med(600, "hpa-utilization", "simulation_lag") * 100, self.med(600, "hpa-concurrency", "simulation_lag") * 100
        self.assertEqual(round(lag_u, 1), round(lag_c, 1))
        self.assertIn(f"level at 600 s ({lag_u:.1f}% each)", self.README)
        misses = [(r["cluster"]["goodput"] - r["simulation_lag"]["goodput"]) * 100 for ramp in self.RAMPS for r in self.rows(ramp, "hpa-utilization")]
        self.assertGreater(min(misses), 0)   # the cluster is above the lagged model on every seed of every ramp
        at_600 = misses[-3:]
        self.assertIn(f"misses utilization's lead at 600 s by {min(at_600):.1f}–{max(at_600):.1f} points", self.README)
        self.assertIn(f"by {min(misses):.1f} to {max(misses):.1f} points, so a fixed 30 s lag charges utilization too much", self.README)

    def test_static_24_serves_the_same_share_on_every_ramp(self):
        shares = [self.med(r, "static-24", "cluster") * 100 for r in self.RAMPS]
        self.assertIn(f"`static-24` serves {min(shares):.1f}–{max(shares):.1f}% on every ramp on the cluster", self.README)
        for ramp in self.RAMPS:
            for side in ("simulation", "simulation_pods", "simulation_lag"):
                self.assertGreater(self.med(ramp, "static-24", side), 0.99)


class RampTests(unittest.TestCase):
    """results/ramps: the same deployment on four ramps; the README's ramp section, claim by claim."""

    RAMPS = (30, 120, 300, 600)

    def doc(self, ramp):
        return results.read(ROOT / "results" / "ramps" / f"ramp-{ramp}")

    def runs(self, ramp, policy):
        return {r["seed"]: r for r in self.doc(ramp)["runs"] if r["policy"] == policy}

    def test_the_four_ramps_differ_only_in_how_long_the_ramp_takes(self):
        loaded = [workload.load(ROOT / "workloads" / f"ramp-{r}.json") for r in self.RAMPS]
        for ramp, w in zip(self.RAMPS, loaded):
            with self.subTest(ramp=ramp):
                self.assertEqual(w.schedule[1:3], ((300.0, 3.0), (300.0 + ramp, 20.0)))
                sizes = lambda x: (x.prompt_median, x.prompt_sigma, x.prompt_max, x.output_median, x.output_sigma, x.output_max, x.slo_ttft_s)
                self.assertEqual(sizes(w), sizes(workload.load(ROOT / "workloads/burst.json")))

    def test_every_dataset_is_the_makefiles_and_regenerates_exactly(self):
        from inference_autoscaling_bench import chart
        self.assertEqual(sorted(p.parent.name for p in (ROOT / "results" / "ramps").glob("*/runs.json")),
                         sorted(f"ramp-{r}" for r in self.RAMPS))
        self.assertIn("for r in 30 120 300 600", (ROOT / "Makefile").read_text())
        for ramp in self.RAMPS:
            with self.subTest(ramp=ramp):
                d = ROOT / "results" / "ramps" / f"ramp-{ramp}"
                doc = results.read(d)
                self.assertEqual([p["label"] for p in doc["policies"]], ["static-24", "hpa-concurrency", "hpa-utilization", "cluster-like"])
                self.assertEqual(sorted({r["seed"] for r in doc["runs"]}), list(range(1, 9)))
                self.assertEqual((d / "README.md").read_text(), report.markdown(doc))
                self.assertEqual((d / "chart.svg").read_text(), chart.svg(doc))

    def test_the_first_run_of_every_policy_is_reproduced_from_its_spec(self):
        for ramp in self.RAMPS:
            doc = self.doc(ramp)
            w = workload.load(ROOT / "workloads" / f"ramp-{ramp}.json")
            trace = workload.generate(w, 1)
            for policy in doc["policies"]:
                with self.subTest(ramp=ramp, policy=policy["label"]):
                    s = spec.parse(policy["text"])
                    got = metrics.summarize(sim.simulate(trace, w, s.make(), s.replica, Bounds(), s.sync_s, s.pod_queues, 1,
                                                         s.metrics_lag_s), w)
                    saved = next(r for r in doc["runs"] if r["policy"] == policy["label"] and r["seed"] == 1)
                    self.assertAlmostEqual(saved["goodput"], got["goodput"], places=12)
                    self.assertAlmostEqual(saved["ttft_p95_ms"], got["ttft_p95_ms"], places=6)

    def test_concurrency_rises_with_every_longer_ramp_in_every_run_and_the_readme_quotes_the_medians(self):
        for seed in range(1, 9):
            g = [self.runs(r, "hpa-concurrency")[seed]["goodput"] for r in self.RAMPS]
            self.assertEqual(g, sorted(g), seed)
            self.assertEqual(len(set(g)), 4)
        quoted = ", ".join(f"{median(f'ramps/ramp-{r}', 'hpa-concurrency', 'goodput') * 100:.1f}%" for r in self.RAMPS[:3])
        self.assertIn(f"{quoted} and {median('ramps/ramp-600', 'hpa-concurrency', 'goodput') * 100:.1f}%", FLAT)

    def test_at_600_s_concurrency_costs_the_quoted_share_of_the_static_pool(self):
        c, s = self.runs(600, "hpa-concurrency"), self.runs(600, "static-24")
        shares = [c[i]["replica_seconds"] / s[i]["replica_seconds"] for i in c]
        self.assertIn(f"costs {min(shares) * 100:.0f}–{max(shares) * 100:.0f}% of `static-24`", FLAT)

    def test_the_better_signal_flips_between_the_short_and_the_long_ramps_in_every_run(self):
        for ramp, utilization_wins in ((30, False), (120, False), (300, True), (600, True)):
            u, c = self.runs(ramp, "hpa-utilization"), self.runs(ramp, "hpa-concurrency")
            for seed in c:
                with self.subTest(ramp=ramp, seed=seed):
                    self.assertEqual(u[seed]["goodput"] >= c[seed]["goodput"], utilization_wins)

    def test_cluster_like_is_below_concurrency_everywhere_and_never_above_the_quoted_ceiling(self):
        top = 0.0
        for ramp in self.RAMPS:
            k, c = self.runs(ramp, "cluster-like"), self.runs(ramp, "hpa-concurrency")
            for seed in c:
                self.assertLess(k[seed]["goodput"], c[seed]["goodput"], (ramp, seed))
            top = max(top, max(r["goodput"] for r in k.values()))
        self.assertIn(f"no run serves more than {top * 100:.1f}% in time", FLAT)

    def test_on_the_600_s_ramp_the_queue_per_pod_costs_more_than_the_lag_and_static_24_barely_notices(self):
        from inference_autoscaling_bench import experiment
        w = workload.load(ROOT / "workloads/ramp-600.json")
        specs = [spec.parse(s) for s in ("pod=hpa-concurrency:route=pod", "lag=hpa-concurrency:lag=30", "s24=static-24:route=pod")]
        rows, _ = experiment.run_matrix(w, specs, list(range(1, 9)), Bounds())
        med = lambda label: statistics.median(r["goodput"] for r in rows if r["policy"] == label) * 100
        self.assertLess(med("pod"), med("lag"))
        self.assertIn(f"a queue per pod alone gives {med('pod'):.1f}% and the lag alone {med('lag'):.1f}%", FLAT)
        self.assertIn(f"`static-24` with a queue per pod serves {med('s24'):.1f}%", FLAT)


class SampledPipelineTests(unittest.TestCase):
    """The fourth model, with each pod's sample given its own age: the README's two bullets on it, number by number."""

    RAMPS = (30, 120, 300, 600)
    DOCS = {r: results.read(ROOT / "results" / "cluster-ramps" / f"ramp-{r}") for r in RAMPS}
    BURST = results.read(ROOT / "results" / "cluster")
    README = " ".join((ROOT / "README.md").read_text().split())

    def rows(self, doc, policy):
        return sorted((r for r in doc["rows"] if r["policy"] == policy), key=lambda r: r["seed"])

    def med(self, doc, policy, side, key="goodput"):
        return statistics.median(r[side][key] for r in self.rows(doc, policy))

    def series(self, policy, side):
        return [self.med(self.DOCS[r], policy, side) * 100 for r in self.RAMPS]

    @staticmethod
    def quoted(values):
        return ", ".join(f"{v:.1f}%" for v in values[:-1]) + f" and {values[-1]:.1f}%"

    def test_every_comparison_carries_the_fourth_model_and_regenerates(self):
        from inference_autoscaling_bench import compare
        for name, doc in {"cluster": self.BURST, **{f"cluster-ramps/ramp-{r}": d for r, d in self.DOCS.items()}}.items():
            with self.subTest(comparison=name):
                for row in doc["rows"]:
                    self.assertEqual(set(row["simulation_scrape"]), set(row["simulation_lag"]))
                self.assertEqual((ROOT / "results" / name / "README.md").read_text(), compare.markdown(doc))

    def test_the_fourth_model_is_the_spec_it_says(self):
        from inference_autoscaling_bench import compare
        burst = workload.load(ROOT / "workloads/burst.json")
        row = self.rows(self.BURST, "hpa-utilization")[0]
        run = {"config": row["config"], "summary": {"policy": "hpa-utilization", "seed": row["seed"]}}
        got = compare.simulate_like(run, burst, pod_queues=True, scrape_s=15)
        self.assertEqual(set(got), set(row["simulation_scrape"]))
        for key, value in got.items():   # the last digit of a mean differs between Python versions
            self.assertAlmostEqual(row["simulation_scrape"][key], value, delta=abs(value) * 1e-9 + 1e-9, msg=key)

    def test_the_burst_numbers_and_the_largest_median_gaps(self):
        g = lambda p, side: self.med(self.BURST, p, side) * 100
        t = lambda p, side: round(self.med(self.BURST, p, side, "ttft_p95_ms") / 1000)
        self.assertIn(f"`hpa-utilization` from {g('hpa-utilization', 'simulation_lag'):.1f}% to {g('hpa-utilization', 'simulation_scrape'):.1f}% "
                      f"against {g('hpa-utilization', 'cluster'):.1f}% on the cluster, and its tail from {t('hpa-utilization', 'simulation_lag')} s "
                      f"to {t('hpa-utilization', 'simulation_scrape')} s against {t('hpa-utilization', 'cluster')} s", self.README)
        for p in ("hpa-queue", "hpa-concurrency"):
            self.assertIn(f"`{p}` from {g(p, 'simulation_lag'):.1f}% to {g(p, 'simulation_scrape'):.1f}% against {g(p, 'cluster'):.1f}%", self.README)
        hpa = ("hpa-concurrency", "hpa-queue", "hpa-utilization")
        gap = lambda side: max(abs(g(p, side) - g(p, "cluster")) for p in hpa)
        self.assertGreater(gap("simulation_scrape"), gap("simulation_lag"))
        self.assertIn(f"largest median gap on the burst is {gap('simulation_scrape'):.1f} points against the fixed lag's {gap('simulation_lag'):.1f}", self.README)

    def test_the_flip_and_utilizations_lead_fall_where_the_cluster_puts_them_on_every_seed(self):
        for ramp in self.RAMPS:
            for u, c in zip(self.rows(self.DOCS[ramp], "hpa-utilization"), self.rows(self.DOCS[ramp], "hpa-concurrency")):
                with self.subTest(ramp=ramp, seed=u["seed"]):
                    self.assertEqual(u["simulation_scrape"]["goodput"] > c["simulation_scrape"]["goodput"], ramp == 600)
                    self.assertEqual(u["cluster"]["goodput"] > c["cluster"]["goodput"], ramp == 600)
        d = self.DOCS[600]
        u, c = self.med(d, "hpa-utilization", "simulation_scrape") * 100, self.med(d, "hpa-concurrency", "simulation_scrape") * 100
        tails = (self.med(d, "hpa-utilization", "simulation_scrape", "ttft_p95_ms") / 1000, self.med(d, "hpa-concurrency", "simulation_scrape", "ttft_p95_ms") / 1000)
        self.assertLess(tails[0], tails[1])
        self.assertIn(f"above it on the 600 s ramp ({u:.1f}% against {c:.1f}%, with a shorter tail, {tails[0]:.1f} s against {tails[1]:.1f} s", self.README)

    def test_utilization_is_within_the_quoted_points_and_the_fixed_lag_is_not(self):
        scrape, cluster = self.series("hpa-utilization", "simulation_scrape"), self.series("hpa-utilization", "cluster")
        self.assertIn(f"For `hpa-utilization` it says {self.quoted(scrape)} against the cluster's {self.quoted(cluster)}", self.README)
        def gaps(side):
            seeds = [abs(r["cluster"]["goodput"] - r[side]["goodput"]) * 100 for ramp in self.RAMPS for r in self.rows(self.DOCS[ramp], "hpa-utilization")]
            meds = [abs(a - b) for a, b in zip(self.series("hpa-utilization", side), cluster)]
            return max(seeds), max(meds)
        self.assertLess(gaps("simulation_scrape"), gaps("simulation_lag"))
        self.assertIn(f"within {gaps('simulation_scrape')[0]:.1f} points on every seed and {gaps('simulation_scrape')[1]:.1f} on the medians, "
                      f"where the fixed lag is within {gaps('simulation_lag')[0]:.1f} and {gaps('simulation_lag')[1]:.1f}", self.README)

    def test_concurrency_sits_above_the_cluster_on_every_ramp_and_the_fixed_lag_is_closer_on_every_one(self):
        scrape, lag, cluster = (self.series("hpa-concurrency", side) for side in ("simulation_scrape", "simulation_lag", "cluster"))
        self.assertTrue(all(s > c for s, c in zip(scrape, cluster)))
        self.assertIn(f"For `hpa-concurrency` it says {self.quoted(scrape)}, above the cluster on every ramp", self.README)
        seeds = lambda side: max(abs(r["cluster"]["goodput"] - r[side]["goodput"]) * 100 for ramp in self.RAMPS for r in self.rows(self.DOCS[ramp], "hpa-concurrency"))
        self.assertIn(f"within {seeds('simulation_scrape'):.1f} points on every seed, where the fixed lag is within {seeds('simulation_lag'):.1f} "
                      "and closer on every ramp's median", self.README)
        for i, ramp in enumerate(self.RAMPS):
            with self.subTest(ramp=ramp):
                self.assertLess(abs(lag[i] - cluster[i]), abs(scrape[i] - cluster[i]))


class KedaModelTests(unittest.TestCase):
    """results/keda/model: the HPA and KEDA on each signal in the model, committed before the cluster ran them."""
    DIR = ROOT / "results" / "keda" / "model"

    def test_it_is_what_the_makefile_builds_and_its_report_and_chart_regenerate(self):
        self.assertIn("--out results/keda/model", (ROOT / "Makefile").read_text())
        doc = results.read(self.DIR)
        self.assertEqual((self.DIR / "README.md").read_text(), report.markdown(doc))
        self.assertEqual((self.DIR / "chart.svg").read_text(), __import__("inference_autoscaling_bench.chart", fromlist=["svg"]).svg(doc))

    def test_every_signal_runs_both_ways_on_eight_seeds_with_the_cluster_pipeline(self):
        doc = results.read(self.DIR)
        for signal in ("concurrency", "queue", "utilization"):
            for scaler in ("hpa", "keda"):
                with self.subTest(policy=f"{scaler}-{signal}"):
                    text = next(p["text"] for p in doc["policies"] if p["label"] == f"{scaler}-{signal}")
                    self.assertEqual(text, f"{scaler}-{signal}={scaler}-{signal}:route=pod,scrape=15")
                    self.assertEqual(sorted(r["seed"] for r in doc["runs"] if r["policy"] == f"{scaler}-{signal}"), list(range(1, 9)))

    def test_the_first_run_of_every_policy_is_reproduced_from_its_spec(self):
        from inference_autoscaling_bench.experiment import run_matrix
        doc = results.read(self.DIR)
        w = workload.load(ROOT / "workloads" / "burst.json")
        for policy in doc["policies"]:
            with self.subTest(policy=policy["label"]):
                rows, _ = run_matrix(w, [spec.parse(policy["text"])], [1], Bounds(policy["min_replicas"], doc["bounds"]["max_replicas"]))
                saved = next(r for r in doc["runs"] if r["policy"] == policy["label"] and r["seed"] == 1)
                for key, value in rows[0].items():
                    if key not in ("policy", "seed"):
                        self.assertAlmostEqual(saved[key], value, delta=abs(value) * 1e-9 + 1e-9, msg=key)

    def test_the_model_predicts_the_same_decisions_on_concurrency_and_few_differences_elsewhere(self):
        doc = results.read(self.DIR)
        def runs(policy):
            return {r["seed"]: r for r in doc["runs"] if r["policy"] == policy}
        differ = {}
        for signal in ("concurrency", "queue", "utilization"):
            hpa, keda = runs(f"hpa-{signal}"), runs(f"keda-{signal}")
            differ[signal] = sum(hpa[s]["replica_seconds"] != keda[s]["replica_seconds"] for s in hpa)
        self.assertEqual(differ, {"concurrency": 0, "queue": 1, "utilization": 3})


class KedaClusterBurstTests(unittest.TestCase):
    """results/keda/cluster-burst: the HPA and KEDA on each signal on the cluster, one dispatch, three seeds each."""
    DIR = ROOT / "results" / "keda" / "cluster-burst"

    def test_every_signal_ran_both_ways_on_the_same_three_seeds(self):
        doc = compare.read(self.DIR)
        self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["rows"]),
                         sorted((f"{scaler}-{signal}", seed) for scaler in ("hpa", "keda")
                                for signal in ("concurrency", "queue", "utilization") for seed in (1, 2, 3)))
        for row in doc["rows"]:
            self.assertEqual(row["config"], {"startup_s": 45.0, "min_replicas": 2, "max_replicas": 32, "down_window_s": 300.0,
                                             "workload": "burst"})

    def test_the_readme_regenerates_from_the_runs(self):
        self.assertEqual((self.DIR / "README.md").read_text(), compare.markdown(compare.read(self.DIR)))


class KedaClaimTests(unittest.TestCase):
    """The README's KEDA bullets, number by number."""
    DOC = compare.read(ROOT / "results" / "keda" / "cluster-burst")
    MODEL = results.read(ROOT / "results" / "keda" / "model")

    def rows(self, policy):
        return sorted((r for r in self.DOC["rows"] if r["policy"] == policy), key=lambda r: r["seed"])

    def cluster(self, policy, key):
        return [r["cluster"][key] for r in self.rows(policy)]

    @staticmethod
    def pct(values):
        return ", ".join(f"{v * 100:.1f}%" for v in values[:-1]) + f" and {values[-1] * 100:.1f}%"

    def test_the_prediction_quoted_is_the_model_dataset(self):
        self.assertIn("on utilization 1.5 points of goodput (42.5% to 44.0%)", FLAT)
        hpa = statistics.median(r["goodput"] for r in self.MODEL["runs"] if r["policy"] == "hpa-utilization")
        keda = statistics.median(r["goodput"] for r in self.MODEL["runs"] if r["policy"] == "keda-utilization")
        self.assertEqual((f"{hpa * 100:.1f}", f"{keda * 100:.1f}", f"{(keda - hpa) * 100:.1f}"), ("42.5", "44.0", "1.5"))

    def test_keda_on_utilization_served_more_in_every_seed_for_more_pods(self):
        hpa, keda = self.cluster("hpa-utilization", "goodput"), self.cluster("keda-utilization", "goodput")
        self.assertTrue(all(k > h for h, k in zip(hpa, keda)))
        self.assertGreater(min(keda), max(hpa))
        self.assertIn(f"Goodput {statistics.median(keda) * 100:.1f}% against {statistics.median(hpa) * 100:.1f}% "
                      f"({self.pct(keda)} against {self.pct(hpa)})", FLAT)
        p50 = [statistics.median(self.cluster(p, "ttft_p50_ms")) / 1000 for p in ("keda-utilization", "hpa-utilization")]
        self.assertIn(f"the median first token {p50[0]:.1f} s against {p50[1]:.1f} s", FLAT)
        unhealthy = [statistics.median(self.cluster(p, "unhealthy_s")) for p in ("keda-utilization", "hpa-utilization")]
        self.assertIn(f"{unhealthy[0]:,.0f} unhealthy seconds against {unhealthy[1]:,.0f}", FLAT)
        cost_h, cost_k = self.cluster("hpa-utilization", "replica_seconds"), self.cluster("keda-utilization", "replica_seconds")
        self.assertTrue(all(k > h for h, k in zip(cost_h, cost_k)))
        ratio = statistics.median(cost_k) / statistics.median(cost_h) - 1
        self.assertIn(f"at {ratio * 100:.0f}% more replica-seconds ({statistics.median(cost_k):,.0f} against "
                      f"{statistics.median(cost_h):,.0f}), more in every seed", FLAT)

    def test_no_difference_held_on_concurrency_and_queue(self):
        for signal, quoted in (("concurrency", "77.3% against 76.3%"), ("queue", "79.7% against 77.9%")):
            hpa, keda = self.cluster(f"hpa-{signal}", "goodput"), self.cluster(f"keda-{signal}", "goodput")
            with self.subTest(signal=signal):
                self.assertEqual(sum(k < h for h, k in zip(hpa, keda)), 2)
                self.assertEqual(f"{statistics.median(keda) * 100:.1f}% against {statistics.median(hpa) * 100:.1f}%", quoted)
                self.assertIn(quoted, FLAT)

    def test_the_hpas_side_repeats_the_first_cluster_dataset_within_a_point(self):
        first = sorted((r for r in compare.read(ROOT / "results" / "cluster")["rows"] if r["policy"] == "hpa-utilization"),
                       key=lambda r: r["seed"])
        now = self.cluster("hpa-utilization", "goodput")
        then = [r["cluster"]["goodput"] for r in first]
        self.assertTrue(all(abs(a - b) < 0.01 for a, b in zip(now, then)))
        self.assertIn(f"served {self.pct(now)} against {self.pct(then)}", FLAT)
        second = [r["cluster"]["goodput"] for r in sorted(compare.read(ROOT / "results" / "keda" / "cluster-burst-utilization")["rows"],
                                                           key=lambda r: r["seed"]) if r["policy"] == "hpa-utilization"]
        moved = [abs(a - b) for a, b in zip(now, second)]
        self.assertEqual(moved.index(max(moved)), 1)   # seed 2
        self.assertIn(f"moved it by up to {max(moved) * 100:.1f} points on seed 2", FLAT)


class KedaClusterRampTests(unittest.TestCase):
    """results/keda/cluster-ramp-30: the HPA and KEDA on concurrency and utilization on the 30 s ramp, three seeds each."""
    DIR = ROOT / "results" / "keda" / "cluster-ramp-30"

    def test_both_signals_ran_both_ways_on_the_same_three_seeds(self):
        doc = compare.read(self.DIR)
        self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["rows"]),
                         sorted((f"{scaler}-{signal}", seed) for scaler in ("hpa", "keda")
                                for signal in ("concurrency", "utilization") for seed in (1, 2, 3)))
        self.assertEqual({r["config"]["workload"] for r in doc["rows"]}, {"ramp-30"})

    def test_the_readme_regenerates_from_the_runs(self):
        self.assertEqual((self.DIR / "README.md").read_text(), compare.markdown(compare.read(self.DIR)))


class KedaRampClaimTests(unittest.TestCase):
    """The README's 30 s ramp bullet in the KEDA section, number by number."""
    DOC = compare.read(ROOT / "results" / "keda" / "cluster-ramp-30")
    FIRST = compare.read(ROOT / "results" / "cluster-ramps" / "ramp-30")

    @staticmethod
    def values(doc, policy, key="goodput"):
        return [r["cluster"][key] for r in sorted(doc["rows"], key=lambda r: r["seed"]) if r["policy"] == policy]

    def test_keda_on_utilization_was_worse_on_every_seed_by_the_quoted_points(self):
        hpa, keda = self.values(self.DOC, "hpa-utilization"), self.values(self.DOC, "keda-utilization")
        gaps = [h - k for h, k in zip(hpa, keda)]
        self.assertTrue(all(g > 0 for g in gaps))
        self.assertIn(f"({statistics.median(keda) * 100:.1f}% against {statistics.median(hpa) * 100:.1f}% at the median), by "
                      f"{gaps[0] * 100:.1f}, {gaps[1] * 100:.1f} and {gaps[2] * 100:.1f} points", FLAT)

    def test_on_concurrency_keda_was_better_on_two_seeds_and_cheaper_on_all(self):
        hpa, keda = self.values(self.DOC, "hpa-concurrency"), self.values(self.DOC, "keda-concurrency")
        self.assertEqual(sum(k > h for h, k in zip(hpa, keda)), 2)
        self.assertIn(f"better on two seeds of three ({statistics.median(keda) * 100:.1f}% against "
                      f"{statistics.median(hpa) * 100:.1f}%)", FLAT)
        cost_h, cost_k = self.values(self.DOC, "hpa-concurrency", "replica_seconds"), self.values(self.DOC, "keda-concurrency", "replica_seconds")
        self.assertTrue(all(k < h for h, k in zip(cost_h, cost_k)))

    def test_the_hpas_utilization_runs_were_above_the_committed_ramps_on_every_seed(self):
        above = [a - b for a, b in zip(self.values(self.DOC, "hpa-utilization"), self.values(self.FIRST, "hpa-utilization"))]
        self.assertTrue(all(a > 0 for a in above))
        self.assertIn(f"{min(above) * 100:.1f} to {max(above) * 100:.1f} points above the committed ramp's on each seed", FLAT)


class KedaThreeWayTests(unittest.TestCase):
    """results/keda/cluster-burst-utilization: the HPA, the external HPA and KEDA on utilization, the burst again."""
    DIR = ROOT / "results" / "keda" / "cluster-burst-utilization"

    def test_the_three_paths_ran_on_the_same_three_seeds_as_the_first_dispatch(self):
        doc = compare.read(self.DIR)
        self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["rows"]),
                         sorted((f"{path}-utilization", seed) for path in ("hpa", "external", "keda") for seed in (1, 2, 3)))
        first = compare.read(ROOT / "results" / "keda" / "cluster-burst")
        self.assertEqual({json_config(r) for r in doc["rows"]}, {json_config(r) for r in first["rows"]})

    def test_the_readme_regenerates_and_sets_every_path_against_the_others(self):
        text = (self.DIR / "README.md").read_text()
        self.assertEqual(text, compare.markdown(compare.read(self.DIR)))
        for title in ("KEDA against the HPA", "The external HPA against the HPA", "KEDA against the external HPA"):
            self.assertIn(f"### {title}, on the cluster", text)


def json_config(row):
    return tuple(sorted(row["config"].items()))


class KedaSecondDispatchClaimTests(unittest.TestCase):
    """The README's bullets on the second burst dispatch and the two dispatches together."""
    FIRST = compare.read(ROOT / "results" / "keda" / "cluster-burst")
    SECOND = compare.read(ROOT / "results" / "keda" / "cluster-burst-utilization")

    @staticmethod
    def goodput(doc, policy):
        return [r["cluster"]["goodput"] for r in sorted(doc["rows"], key=lambda r: r["seed"]) if r["policy"] == policy]

    def test_keda_was_behind_on_every_seed_the_second_time(self):
        hpa, keda = self.goodput(self.SECOND, "hpa-utilization"), self.goodput(self.SECOND, "keda-utilization")
        external = self.goodput(self.SECOND, "external-utilization")
        self.assertTrue(all(k < h for h, k in zip(hpa, keda)))
        self.assertIn(f"KEDA served {statistics.median(keda) * 100:.1f}% against the HPA's {statistics.median(hpa) * 100:.1f}% "
                      f"at the median, below it on every seed, and the external HPA {statistics.median(external) * 100:.1f}%", FLAT)

    def test_keda_moved_between_dispatches_as_much_as_the_first_gap(self):
        moved = [abs(a - b) for a, b in zip(self.goodput(self.FIRST, "keda-utilization"), self.goodput(self.SECOND, "keda-utilization"))]
        self.assertIn(f"KEDA's own runs moved by {min(moved) * 100:.1f} to {max(moved) * 100:.1f} points", FLAT)
        gap = statistics.median(self.goodput(self.FIRST, "keda-utilization")) - statistics.median(self.goodput(self.FIRST, "hpa-utilization"))
        self.assertGreater(max(moved), gap)

    def test_over_both_dispatches_keda_led_on_every_seed_once_and_trailed_on_every_seed_once(self):
        both = {p: self.goodput(self.FIRST, p) + self.goodput(self.SECOND, p) for p in ("hpa-utilization", "keda-utilization")}
        self.assertIn(f"KEDA's median is {statistics.median(both['keda-utilization']) * 100:.1f}% and the HPA's "
                      f"{statistics.median(both['hpa-utilization']) * 100:.1f}%", FLAT)
        first = [k > h for h, k in zip(self.goodput(self.FIRST, "hpa-utilization"), self.goodput(self.FIRST, "keda-utilization"))]
        second = [k > h for h, k in zip(self.goodput(self.SECOND, "hpa-utilization"), self.goodput(self.SECOND, "keda-utilization"))]
        self.assertEqual((first, second), ([True] * 3, [False] * 3))
        self.assertNotIn("most of that is the path", FLAT)


class PredictiveDatasetTests(unittest.TestCase):
    """results/predictive: the HPA beside the predictive policy on the burst and the four ramps."""

    WORKLOADS = ("burst", "ramp-30", "ramp-120", "ramp-300", "ramp-600")
    LABELS = ["static-24", "hpa-concurrency", "predict-concurrency", "hpa-rps", "predict-rps", "warm-12", "cluster-like",
              "predict-cluster-like"]

    def test_every_dataset_is_the_makefiles_and_regenerates_exactly(self):
        from inference_autoscaling_bench import chart
        self.assertEqual(sorted(p.parent.name for p in (ROOT / "results" / "predictive").glob("*/runs.json")), sorted(self.WORKLOADS))
        self.assertIn("for w in " + " ".join(self.WORKLOADS) + ";", (ROOT / "Makefile").read_text())
        for name in self.WORKLOADS:
            with self.subTest(workload=name):
                d = ROOT / "results" / "predictive" / name
                doc = results.read(d)
                self.assertEqual([p["label"] for p in doc["policies"]], self.LABELS)
                self.assertEqual(sorted((r["policy"], r["seed"]) for r in doc["runs"]),
                                 sorted((label, seed) for label in self.LABELS for seed in range(1, 9)))
                self.assertEqual((d / "README.md").read_text(), report.markdown(doc))
                self.assertEqual((d / "chart.svg").read_text(), chart.svg(doc))

    def test_ci_regenerates_the_dataset_and_fails_on_any_difference(self):
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        reproduce = ci[ci.index("  reproduce:"):]
        self.assertIn("make results-predictive", reproduce)
        self.assertLess(reproduce.index("make results-predictive"), reproduce.index("git diff --exit-code -- results"))

    def test_the_policies_are_the_ones_the_methodology_fixed_before_the_runs(self):
        doc = results.read(ROOT / "results" / "predictive" / "burst")
        texts = {p["label"]: p["text"] for p in doc["policies"]}
        self.assertEqual(texts["predict-concurrency"], "predict-concurrency")
        self.assertEqual(texts["warm-12"], "warm-12=hpa-concurrency:min=12")
        self.assertEqual(texts["predict-cluster-like"], "predict-cluster-like=predict-concurrency:route=pod,scrape=15")
        methodology = " ".join((ROOT / "docs" / "methodology.md").read_text().split())
        for label in self.LABELS:
            self.assertIn(f"`{label}`", methodology)

    def test_the_first_run_of_every_policy_is_reproduced_from_its_spec(self):
        from inference_autoscaling_bench.experiment import run_matrix
        for name in self.WORKLOADS:
            doc = results.read(ROOT / "results" / "predictive" / name)
            w = workload.load(ROOT / "workloads" / f"{name}.json")
            for policy in doc["policies"]:
                with self.subTest(workload=name, policy=policy["label"]):
                    rows, _ = run_matrix(w, [spec.parse(policy["text"])], [1], Bounds(policy["min_replicas"], doc["bounds"]["max_replicas"]))
                    saved = next(r for r in doc["runs"] if r["policy"] == policy["label"] and r["seed"] == 1)
                    for key in ("goodput", "ttft_p95_ms", "replica_seconds"):
                        self.assertAlmostEqual(saved[key], rows[0][key], delta=abs(rows[0][key]) * 1e-9 + 1e-9, msg=key)


class PredictiveClaimTests(unittest.TestCase):
    """The README's predictive section, claim by claim."""

    def runs(self, name, policy):
        return {r["seed"]: r for r in results.read(ROOT / "results" / "predictive" / name)["runs"] if r["policy"] == policy}

    def tally(self, name, a, b, key="goodput"):
        """(runs where a is higher, runs where they are equal, runs where a is lower)."""
        x, y = self.runs(name, a), self.runs(name, b)
        higher = sum(x[s][key] > y[s][key] for s in x)
        equal = sum(x[s][key] == y[s][key] for s in x)
        return higher, equal, len(x) - higher - equal

    def med(self, name, policy, key):
        return statistics.median(r[key] for r in self.runs(name, policy).values())

    def test_on_the_300_s_ramp_the_forecast_serves_more_with_a_shorter_tail_in_every_run_and_mostly_costs_less(self):
        self.assertEqual(self.tally("ramp-300", "predict-concurrency", "hpa-concurrency"), (8, 0, 0))
        self.assertEqual(self.tally("ramp-300", "predict-concurrency", "hpa-concurrency", "ttft_p95_ms"), (0, 0, 8))
        self.assertEqual(self.tally("ramp-300", "predict-concurrency", "hpa-concurrency", "replica_seconds"), (2, 0, 6))
        g = lambda p: f"{self.med('ramp-300', p, 'goodput') * 100:.1f}%"
        ms = lambda p: f"{self.med('ramp-300', p, 'ttft_p95_ms'):,.0f} ms"
        cost = lambda p: f"{self.med('ramp-300', p, 'replica_seconds'):,.0f}"
        self.assertIn(f"`predict-concurrency` serves {g('predict-concurrency')} of requests in time against "
                      f"{g('hpa-concurrency')} for `hpa-concurrency`, with a shorter tail ({ms('predict-concurrency')} "
                      f"against {ms('hpa-concurrency')} at the 95th percentile), in every run, and costs less in 6 of 8 "
                      f"runs ({cost('predict-concurrency')} against {cost('hpa-concurrency')} replica-seconds", FLAT)

    def test_on_the_120_and_600_s_ramps_it_serves_more_in_seven_runs_and_the_same_in_the_eighth(self):
        for name in ("ramp-120", "ramp-600"):
            with self.subTest(workload=name):
                self.assertEqual(self.tally(name, "predict-concurrency", "hpa-concurrency"), (7, 1, 0))
        self.assertIn("On the 120 s and 600 s ramps it serves more in 7 of 8 runs and the same in the eighth.", FLAT)

    def test_on_the_fastest_ramps_the_hpa_already_asks_past_the_scale_up_limit_so_the_forecast_changes_nothing(self):
        import math
        from inference_autoscaling_bench.policies import Predictive

        class Watched(Predictive):
            def decide(self, obs, bounds):
                current = obs.ready + obs.pending
                if 300 <= obs.now <= 420 and current < bounds.max_replicas and obs.ready:
                    self.seen.append((current, self.recommend(obs), max(current + self.up_pods, math.ceil(current * (1 + self.up_percent / 100)))))
                return super().decide(obs, bounds)

        for name in ("burst", "ramp-30"):
            with self.subTest(workload=name):
                w = workload.load(ROOT / "workloads" / f"{name}.json")
                trace = workload.generate(w, 1)
                watched = Watched("concurrency")
                watched.seen = []
                ahead = sim.simulate(trace, w, watched)
                hpa = sim.simulate(trace, w, spec.parse("hpa-concurrency").make())
                growing = [(rec, cap) for current, rec, cap in watched.seen if rec > current]   # syncs where the HPA asks to grow
                self.assertGreaterEqual(len(growing), 3)
                self.assertTrue(all(rec > cap for rec, cap in growing[1:]), growing)
                during = lambda run: [e for e in run.events if 300 <= e[0] <= 420]
                self.assertEqual(during(ahead), during(hpa))
        self.assertEqual(self.tally("burst", "predict-concurrency", "hpa-concurrency")[1], 5)
        self.assertEqual(self.tally("ramp-30", "predict-concurrency", "hpa-concurrency")[1], 7)
        self.assertIn("serves the same share as `hpa-concurrency` in 5 of 8 runs of the burst and 7 of 8 of the 30 s ramp", FLAT)

    def test_headroom_wins_on_the_fast_ramps_and_the_forecast_is_cheaper_on_the_slow_ones(self):
        for name in ("burst", "ramp-30", "ramp-120"):
            with self.subTest(workload=name):
                self.assertEqual(self.tally(name, "warm-12", "predict-concurrency"), (8, 0, 0))
        costs, points = [], []
        for name in ("ramp-300", "ramp-600"):
            with self.subTest(workload=name):
                self.assertEqual(self.tally(name, "predict-concurrency", "warm-12", "replica_seconds"), (0, 0, 8))
                costs.append(f"{self.med(name, 'predict-concurrency', 'replica_seconds'):,.0f} against "
                             f"{self.med(name, 'warm-12', 'replica_seconds'):,.0f}")
                points.append(f"{(self.med(name, 'warm-12', 'goodput') - self.med(name, 'predict-concurrency', 'goodput')) * 100:.1f}")
        self.assertIn(f"the forecast costs less in every run ({costs[0]} and {costs[1]} replica-seconds at the median) "
                      f"and gives up {points[0]} and {points[1]} points of goodput.", FLAT)
