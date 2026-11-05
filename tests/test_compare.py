import json
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
            self.assertNotIn("source", row["cluster"])

    def test_the_markdown_states_the_setup_and_the_difference(self):
        text = compare.markdown(compare.build("Cluster vs model", SMOKE, [cluster_run(seed=1), cluster_run(seed=2, goodput=0.97)]))
        self.assertIn("## Cluster vs model", text)
        self.assertIn("### `hpa-concurrency`", text)
        self.assertIn("2 seeds (1, 2)", text)
        self.assertIn("Pods start in 20 s, scale-down window 300 s", text)
        self.assertIn("| Metric | Cluster | One shared queue | Queue per pod | Cluster minus one queue | Cluster minus queue per pod |", text)
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
