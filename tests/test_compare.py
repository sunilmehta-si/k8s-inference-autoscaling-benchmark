import json
import re
import tempfile
import unittest
from pathlib import Path

from inference_autoscaling_bench import cli, compare, experiment, spec, workload
from inference_autoscaling_bench.policies import Bounds

ROOT = Path(__file__).resolve().parent.parent
SMOKE = workload.load(ROOT / "workloads/smoke.json")


def cluster_run(policy="hpa-concurrency", seed=1, startup=20.0, **summary):
    base = {"requests": 183, "ttft_p50_ms": 120.0, "ttft_p95_ms": 1300.0, "ttft_p99_ms": 1800.0, "latency_p95_s": 4.0, "goodput": 0.99,
            "unhealthy_s": 0.0, "replica_seconds": 120.0, "mean_replicas": 2.0, "peak_replicas": 2, "max_queue": 1,
            "scale_ups": 0, "scale_downs": 0, "flaps": 0, "replica_seconds_per_good_request": 0.66,
            "policy": policy, "seed": seed, "source": "cluster"}
    base.update(summary)
    return {"summary": base, "config": {"startup_s": startup, "min_replicas": 2, "max_replicas": 32, "down_window_s": 300.0,
                                        "workload": "smoke"},
            "client": {"requests": 183, "answered": 183, "failed": 0}, "events": [], "timeline": [], "sampling": {}}


class SimulateLikeTests(unittest.TestCase):
    def test_the_simulation_gets_the_clusters_policy_seed_and_settings(self):
        run = cluster_run(startup=20.0, seed=2)
        got = compare.simulate_like(run, SMOKE)
        rows, _ = experiment.run_matrix(SMOKE, [spec.parse("hpa-concurrency:startup=20,down=300")], [2], Bounds(2, 32))
        self.assertEqual(got, {k: v for k, v in rows[0].items() if k not in ("policy", "seed")})

    def test_a_different_startup_changes_the_simulation(self):
        burst = workload.load(ROOT / "workloads/burst.json")   # the smoke workload is too short for startup to matter
        a = compare.simulate_like(cluster_run(startup=5.0), burst)
        b = compare.simulate_like(cluster_run(startup=120.0), burst)
        self.assertLess(a["ttft_p95_ms"], b["ttft_p95_ms"])

    def test_a_keda_run_is_simulated_with_its_window_and_the_external_metric(self):
        run = cluster_run(policy="keda-concurrency", seed=2)
        run["config"]["down_window_s"] = 60.0
        got = compare.simulate_like(run, SMOKE)
        rows, _ = experiment.run_matrix(SMOKE, [spec.parse("keda-concurrency:startup=20,down=60")], [2], Bounds(2, 32))
        self.assertEqual(got, {k: v for k, v in rows[0].items() if k not in ("policy", "seed")})

    def test_only_an_autoscaler_has_a_scale_down_window(self):
        self.assertEqual([compare.autoscaled(p) for p in ("hpa-queue", "keda-queue", "external-queue", "static-24")],
                         [True, True, True, False])

    def test_a_static_pool_is_simulated_without_a_scale_down_window(self):
        got = compare.simulate_like(cluster_run(policy="static-4"), SMOKE)
        self.assertEqual((got["peak_replicas"], got["scale_ups"]), (4, 0))


class BuildTests(unittest.TestCase):
    def test_rows_are_ordered_by_policy_then_seed_and_carry_both_sides(self):
        runs = [cluster_run(seed=2), cluster_run(policy="hpa-queue", seed=1), cluster_run(seed=1)]
        doc = compare.build("T", SMOKE, runs)
        self.assertEqual([(r["policy"], r["seed"]) for r in doc["rows"]], [("hpa-concurrency", 1), ("hpa-concurrency", 2), ("hpa-queue", 1)])
        for row in doc["rows"]:
            self.assertIn("goodput", row["cluster"])
            self.assertIn("goodput", row["simulation"])
            self.assertIn("goodput", row["simulation_pods"])
            self.assertIn("goodput", row["simulation_lag"])
            self.assertNotIn("source", row["cluster"])

    def test_the_markdown_states_the_setup_and_the_difference(self):
        text = compare.markdown(compare.build("Cluster vs model", SMOKE, [cluster_run(seed=1), cluster_run(seed=2, goodput=0.97)]))
        self.assertIn("## Cluster vs model", text)
        self.assertIn("### `hpa-concurrency`", text)
        self.assertIn("2 seeds (1, 2)", text)
        self.assertIn("Pods start in 20 s, scale-down window 300 s", text)
        self.assertIn("| Metric | Cluster | One shared queue | Queue per pod | Queue per pod, lag | Queue per pod, scraped "
                      "| Cluster minus one queue | Cluster minus queue per pod | Cluster minus queue per pod, lag "
                      "| Cluster minus queue per pod, scraped |", text)
        self.assertIn("Requests the cluster did not answer: 0 of 366.", text)
        self.assertIn("### Run by run", text)

    def test_one_seed_reads_as_singular(self):
        self.assertIn("1 seed (1)", compare.markdown(compare.build("T", SMOKE, [cluster_run()])))

    def test_goodput_differences_are_in_points_and_signed(self):
        text = compare.markdown(compare.build("T", SMOKE, [cluster_run(goodput=0.5)]))
        line = next(l for l in text.splitlines() if l.startswith("| Goodput"))
        self.assertRegex(line, r"\| -\d+\.\d points \|$")


class LoadTests(unittest.TestCase):
    def test_only_cluster_runs_are_loaded(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "a.json").write_text(json.dumps(cluster_run()))
            (Path(tmp) / "other.json").write_text(json.dumps({"summary": {"source": "simulation"}}))
            self.assertEqual(len(compare.load_cluster_runs(tmp)), 1)

    def test_an_empty_directory_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp, self.assertRaisesRegex(ValueError, "no cluster runs"):
            compare.load_cluster_runs(tmp)

    def test_the_compare_command_writes_the_results_and_the_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs, out = Path(tmp) / "runs", Path(tmp) / "out"
            runs.mkdir()
            (runs / "r.json").write_text(json.dumps(cluster_run()))
            self.assertEqual(cli.main(["compare", str(runs), "--workload", str(ROOT / "workloads/smoke.json"), "--out", str(out)]), 0)
            self.assertEqual(len(json.loads((out / "runs.json").read_text())["rows"]), 1)
            self.assertIn("hpa-concurrency", (out / "README.md").read_text())
            self.assertEqual(compare.read(out)["workload"]["name"], "smoke")


if __name__ == "__main__":
    unittest.main()


class PodQueueTests(unittest.TestCase):
    def test_the_queue_per_pod_simulation_differs_from_the_shared_queue_one_under_load(self):
        burst = workload.load(ROOT / "workloads/burst.json")
        run = cluster_run(startup=45.0)
        one = compare.simulate_like(run, burst)
        per_pod = compare.simulate_like(run, burst, pod_queues=True)
        self.assertGreater(per_pod["ttft_p95_ms"], one["ttft_p95_ms"])

    def test_build_carries_both_simulations(self):
        row = compare.build("T", SMOKE, [cluster_run()])["rows"][0]
        self.assertEqual(set(row["simulation"]), set(row["simulation_pods"]))


class MetricsLagTests(unittest.TestCase):
    def test_the_lag_is_the_scrape_interval_plus_the_rule_interval_on_the_cluster(self):
        text = (ROOT / "deploy/monitoring.yaml").read_text()
        scrape = re.search(r"scrape_interval: (\d+)s", text).group(1)
        rules = re.search(r"^ +interval: (\d+)s", text, re.M).group(1)   # the group that records the HPA signals
        self.assertEqual(compare.METRICS_LAG_S, float(scrape) + float(rules))

    def test_the_lagged_simulation_is_the_queue_per_pod_one_with_the_lag(self):
        burst = workload.load(ROOT / "workloads/burst.json")
        run = cluster_run(startup=45.0)
        lagged = compare.simulate_like(run, burst, pod_queues=True, lag_s=compare.METRICS_LAG_S)
        self.assertNotEqual(lagged, compare.simulate_like(run, burst, pod_queues=True))
        rows, _ = experiment.run_matrix(burst, [spec.parse("hpa-concurrency:startup=45,down=300,route=pod,lag=30")], [1], Bounds(2, 32))
        self.assertEqual(lagged, {k: v for k, v in rows[0].items() if k not in ("policy", "seed")})


class ScrapeModelTests(unittest.TestCase):
    def test_the_interval_is_the_scrape_and_rule_interval_on_the_cluster(self):
        text = (ROOT / "deploy/monitoring.yaml").read_text()
        scrape = re.search(r"scrape_interval: (\d+)s", text).group(1)
        rules = re.search(r"^ +interval: (\d+)s", text, re.M).group(1)
        self.assertEqual((compare.SCRAPE_S, compare.SCRAPE_S), (float(scrape), float(rules)))

    def test_the_scraped_simulation_is_the_queue_per_pod_one_with_the_interval(self):
        burst = workload.load(ROOT / "workloads/burst.json")
        run = cluster_run(startup=45.0)
        scraped = compare.simulate_like(run, burst, pod_queues=True, scrape_s=compare.SCRAPE_S)
        self.assertNotEqual(scraped, compare.simulate_like(run, burst, pod_queues=True))
        self.assertNotEqual(scraped, compare.simulate_like(run, burst, pod_queues=True, lag_s=compare.METRICS_LAG_S))
        rows, _ = experiment.run_matrix(burst, [spec.parse("hpa-concurrency:startup=45,down=300,route=pod,scrape=15")], [1], Bounds(2, 32))
        self.assertEqual(scraped, {k: v for k, v in rows[0].items() if k not in ("policy", "seed")})

    def test_build_carries_the_fourth_model_and_the_markdown_has_its_columns(self):
        doc = compare.build("T", SMOKE, [cluster_run()])
        self.assertIn("goodput", doc["rows"][0]["simulation_scrape"])
        text = compare.markdown(doc)
        self.assertIn("| Queue per pod, lag | Queue per pod, scraped | Cluster minus one queue ", text)
        self.assertIn("| Cluster minus queue per pod, lag | Cluster minus queue per pod, scraped |", text)
        self.assertIn("| Goodput, queue per pod, scraped | TTFT p95 (ms), cluster", text)
        self.assertIn("four runs of the simulation", text)


class RebuildTests(unittest.TestCase):
    def test_rebuild_keeps_the_clusters_side_and_recomputes_the_models(self):
        doc = compare.build("T", SMOKE, [cluster_run(seed=1), cluster_run(seed=2)])
        stale = json.loads(json.dumps(doc))
        for row in stale["rows"]:
            for model in compare.MODELS:
                row[model] = {"goodput": -1.0}
        self.assertEqual(compare.rebuild(stale, SMOKE), doc)

    def test_rebuild_refuses_another_workload(self):
        doc = compare.build("T", SMOKE, [cluster_run()])
        with self.assertRaisesRegex(ValueError, "is of smoke"):
            compare.rebuild(doc, workload.load(ROOT / "workloads/burst.json"))

    def test_the_recompare_command_rewrites_the_results_and_the_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "out"
            compare.write(out, compare.build("T", SMOKE, [cluster_run()]))
            doc = compare.read(out)
            doc["rows"][0]["simulation_scrape"]["goodput"] = -1.0
            compare.write(out, doc)
            self.assertIn("-100.0%", (out / "README.md").read_text())
            self.assertEqual(cli.main(["recompare", str(out), "--workload", str(ROOT / "workloads/smoke.json")]), 0)
            self.assertNotIn("-100.0%", (out / "README.md").read_text())
            self.assertIn("goodput", compare.read(out)["rows"][0]["simulation_scrape"])


def keda_row(policy, seed, **cluster):
    base = {key: 1.0 for key, _, _ in compare.COMPARED}
    base.update(cluster)
    return {"policy": policy, "seed": seed, "cluster": base}


class KedaSectionTests(unittest.TestCase):
    def test_signals_are_paired_on_the_seeds_both_ran(self):
        doc = {"rows": [keda_row("hpa-queue", 1), keda_row("hpa-queue", 2), keda_row("keda-queue", 2), keda_row("keda-queue", 3),
                        keda_row("keda-utilization", 1), keda_row("static-24", 1)]}
        found = compare.pairs(doc)
        self.assertEqual([(s, [r["seed"] for r in h], [r["seed"] for r in k]) for s, h, k in found], [("queue", [2], [2])])

    def test_better_and_worse_follow_each_metrics_direction(self):
        doc = {"rows": [keda_row("hpa-concurrency", 1, goodput=0.80, ttft_p95_ms=900.0, flaps=1.0),
                        keda_row("keda-concurrency", 1, goodput=0.85, ttft_p95_ms=1000.0, flaps=2.0),
                        keda_row("hpa-concurrency", 2, goodput=0.80, ttft_p95_ms=900.0, flaps=1.0),
                        keda_row("keda-concurrency", 2, goodput=0.80, ttft_p95_ms=800.0, flaps=0.0)]}
        text = "\n".join(compare.keda_section(doc))
        self.assertIn("#### concurrency", text)
        self.assertRegex(text, r"\| Goodput \(TTFT within the objective\) \| 80\.0% \| 82\.5% <sub>.*</sub> \| \+2\.5 points \| KEDA better in 1, worse in 0 of 2 \|")
        self.assertRegex(text, r"\| TTFT p95 \(ms\) \| 900 \| .* \| KEDA better in 1, worse in 1 of 2 \|")
        self.assertRegex(text, r"\| Flaps \| 1 \| .* \| KEDA higher in 1, lower in 1 of 2 \|")

    def test_no_section_without_a_signal_run_both_ways(self):
        self.assertEqual(compare.keda_section({"rows": [keda_row("hpa-queue", 1), keda_row("static-24", 1)]}), [])

    def test_the_committed_comparisons_have_no_section_and_are_unchanged(self):
        for path in [ROOT / "results/cluster", *sorted((ROOT / "results/cluster-ramps").iterdir())]:
            with self.subTest(dataset=path.name):
                doc = compare.read(path)
                self.assertNotIn("KEDA", compare.markdown(doc))
                self.assertEqual(compare.markdown(doc), (path / "README.md").read_text())


    def test_the_setup_says_what_a_keda_run_is_only_when_there_is_one(self):
        doc = compare.read(ROOT / "results/cluster")
        self.assertNotIn("A `keda-` run", compare.markdown(doc))
        row = dict(doc["rows"][0], policy="keda-concurrency")
        self.assertIn("A `keda-` run has KEDA in place of prometheus-adapter", compare.markdown({**doc, "rows": doc["rows"] + [row]}))


class MatchupTests(unittest.TestCase):
    ROWS = [keda_row(f"{path}-utilization", seed, goodput=g) for path, goodputs in
            (("hpa", (0.40, 0.39, 0.44)), ("keda", (0.49, 0.47, 0.48)), ("external", (0.48, 0.40, 0.47))) for seed, g in zip((1, 2, 3), goodputs)]

    def test_the_external_hpa_is_set_against_the_hpa_and_keda_against_it(self):
        text = "\n".join(compare.keda_section({"rows": self.ROWS}))
        titles = re.findall(r"^### (.+)$", text, re.M)
        self.assertEqual(titles, ["KEDA against the HPA, on the cluster", "The external HPA against the HPA, on the cluster",
                                  "KEDA against the external HPA, on the cluster"])
        self.assertIn("| Goodput (TTFT within the objective) | 40.0% <sub>(39.0%–44.0%)</sub> | 47.0% <sub>(40.0%–48.0%)</sub> "
                      "| +7.0 points | External HPA better in 3, worse in 0 of 3 |", text)
        self.assertIn("| Metric | External HPA | KEDA | KEDA minus External HPA | Seed by seed |", text)
        self.assertIn("KEDA better in 3, worse in 0 of 3 |", text)

    def test_pairs_take_any_two_paths(self):
        found = compare.pairs({"rows": self.ROWS}, "external", "hpa")
        self.assertEqual([(s, [r["policy"] for r in a], [r["policy"] for r in b]) for s, a, b in found],
                         [("utilization", ["hpa-utilization"] * 3, ["external-utilization"] * 3)])

    def test_without_external_runs_only_keda_against_the_hpa_appears(self):
        rows = [r for r in self.ROWS if not r["policy"].startswith("external-")]
        self.assertEqual(re.findall(r"^### (.+)$", "\n".join(compare.keda_section({"rows": rows})), re.M),
                         ["KEDA against the HPA, on the cluster"])
