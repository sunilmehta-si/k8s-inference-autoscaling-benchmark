import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from inference_autoscaling_bench import cli, results

ROOT = Path(__file__).resolve().parent.parent
SMOKE = str(ROOT / "workloads/smoke.json")


def run_cli(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = cli.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


class CommandTests(unittest.TestCase):
    def test_policies_lists_keda_on_every_signal(self):
        code, out, _ = run_cli("policies")
        self.assertEqual(code, 0)
        for signal in ("concurrency", "queue", "utilization", "rps"):
            self.assertIn(f"keda-{signal}", out)
            self.assertIn(f"external-{signal}", out)

    def test_cluster_run_refuses_a_predictive_policy_before_it_touches_a_cluster(self):
        from unittest import mock
        with mock.patch("inference_autoscaling_bench.cluster.run_on_cluster") as run:
            code, _, err = run_cli("cluster-run", "--policy", "ahead=predict-concurrency", "--workload", SMOKE, "--out", "/nonexistent")
        self.assertIn("modelled only", str(code))
        run.assert_not_called()

    def test_the_readmes_predictive_quick_start_runs(self):
        code, out, _ = run_cli("run", str(ROOT / "workloads/ramp-300.json"), "-p", "hpa-concurrency", "-p", "predict-concurrency")
        self.assertEqual(code, 0)
        self.assertIn("predict-concurrency: ", out)
        self.assertIn("iab run workloads/ramp-300.json -p hpa-concurrency -p predict-concurrency", (ROOT / "README.md").read_text())

    def test_the_cluster_docs_say_a_predictive_policy_is_modelled_only(self):
        docs = " ".join((ROOT / "docs" / "cluster.md").read_text().split())
        self.assertIn("A `predict-` policy is modelled only", docs)
        self.assertIn("`iab cluster-run` refuses one before it touches a cluster", docs)

    def test_policies_lists_predict_on_every_signal_and_its_options(self):
        code, out, _ = run_cli("policies")
        self.assertEqual(code, 0)
        for signal in ("concurrency", "queue", "utilization", "rps"):
            self.assertIn(f"predict-{signal}", out)
        for key in ("horizon", "alpha", "beta", "floor"):
            self.assertIn(key, out)

    def test_policies_lists_every_signal_with_its_default_target(self):
        code, out, _ = run_cli("policies")
        self.assertEqual(code, 0)
        for text in ("static-N", "hpa-utilization", "hpa-concurrency", "hpa-queue", "hpa-rps", "0.6", "key=value"):
            self.assertIn(text, out)

    def test_trace_summarises_a_workload(self):
        code, out, _ = run_cli("trace", SMOKE, "--seed", "1")
        self.assertEqual(code, 0)
        self.assertIn("smoke: 183 requests in 60 s", out)
        self.assertIn("prompt tokens: median", out)

    def test_run_prints_a_line_per_policy(self):
        code, out, _ = run_cli("run", SMOKE, "-p", "static-4", "-p", "hpa-concurrency")
        self.assertEqual(code, 0)
        lines = out.strip().splitlines()
        self.assertEqual([l.split(":")[0] for l in lines], ["static-4", "hpa-concurrency"])
        self.assertIn("goodput 100.0%", lines[0])

    def test_a_bad_spec_is_reported_not_a_traceback(self):
        code, _, err = run_cli("run", SMOKE, "-p", "hpa-gpu")
        self.assertNotEqual(code, 0)
        self.assertIn("unknown policy", str(code) + err)

    def test_a_missing_workload_is_reported(self):
        code, _, err = run_cli("trace", "/nonexistent/w.json")
        self.assertEqual(code, 1)
        self.assertIn("iab:", err)


class MatrixTests(unittest.TestCase):
    def test_matrix_writes_the_results_the_readme_and_the_chart(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "smoke-set"
            code, stdout, _ = run_cli("matrix", SMOKE, "-p", "static-2", "-p", "hpa-queue", "--runs", "3", "--out", str(out),
                                      "--title", "A small set")
            self.assertEqual(code, 0)
            self.assertIn("6 runs written", stdout)
            doc = json.loads((out / "runs.json").read_text())
            self.assertEqual([p["label"] for p in doc["policies"]], ["static-2", "hpa-queue"])
            self.assertEqual(len(doc["runs"]), 6)
            self.assertEqual(sorted(doc["timelines"]), ["hpa-queue", "static-2"])
            self.assertIn("## A small set", (out / "README.md").read_text())
            self.assertTrue((out / "chart.svg").read_text().startswith("<svg"))

    def test_report_renders_the_same_files_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            run_cli("matrix", SMOKE, "-p", "static-2", "-p", "hpa-queue", "--runs", "2", "--out", str(out))
            first = ((out / "README.md").read_text(), (out / "chart.svg").read_text())
            (out / "README.md").write_text("stale")
            (out / "chart.svg").write_text("stale")
            code, _, _ = run_cli("report", str(out))
            self.assertEqual(code, 0)
            self.assertEqual(((out / "README.md").read_text(), (out / "chart.svg").read_text()), first)
            self.assertEqual(results.read(out)["title"], "smoke")

    def test_demand_series_counts_arrivals_per_second_in_each_sync_period(self):
        from inference_autoscaling_bench.workload import Request
        series = results.demand_series([Request(0, 1.0, 1, 1), Request(1, 14.9, 1, 1), Request(2, 16.0, 1, 1)], 45)
        self.assertEqual(series, [[7.5, 2 / 15], [22.5, 1 / 15], [37.5, 0.0]])


if __name__ == "__main__":
    unittest.main()
