import json
import time
import unittest

from inference_autoscaling_bench import cluster
from inference_autoscaling_bench.client import Result
from inference_autoscaling_bench.metrics import summarize
from inference_autoscaling_bench.workload import Request
from tests.helpers import tiny_workload


def pod(ready=True, terminating=False, phase="Running"):
    meta = {"deletionTimestamp": "2026-11-04T00:00:00Z"} if terminating else {}
    return {"metadata": meta, "status": {"phase": phase, "conditions": [{"type": "Ready", "status": "True" if ready else "False"}]}}


class FakeKubectl:
    """Answers the few kubectl calls the cluster module makes, from a mutable state."""

    def __init__(self, context="kind-iab", pods=(), replicas=2, running=3.0, waiting=1.0, prometheus_down=False):
        self.context, self.pods, self.replicas = context, list(pods), replicas
        self.running, self.waiting, self.prometheus_down = running, waiting, prometheus_down
        self.calls = []

    def __call__(self, args, input=None):
        self.calls.append((list(args), input))
        if args[:2] == ["config", "current-context"]:
            return self.context + "\n"
        if "pods" in args and "-o" in args:
            return json.dumps({"items": self.pods})
        if "deployment" in args:
            return str(self.replicas)
        if args[0] == "get" and args[1] == "--raw":
            if self.prometheus_down:
                raise RuntimeError("kubectl get --raw failed: unavailable")
            value = self.running if "running" in args[2] else self.waiting
            return json.dumps({"data": {"result": [{"value": [0, str(value)]}]}})
        return ""


class GuardTests(unittest.TestCase):
    def test_only_the_benchmarks_context_is_accepted(self):
        cluster.require_context(FakeKubectl("kind-iab"))
        for context in ("gke_proj_zone_prod", "kind-irb", "docker-desktop", ""):
            with self.subTest(context=context), self.assertRaisesRegex(RuntimeError, "refusing to run"):
                cluster.require_context(FakeKubectl(context))

    def test_a_kubectl_that_fails_is_a_refusal(self):
        def broken(args, input=None):
            raise RuntimeError("no kubeconfig")
        with self.assertRaisesRegex(RuntimeError, "refusing to run"):
            cluster.require_context(broken)


class CountTests(unittest.TestCase):
    def test_pods_are_ready_pending_or_terminating(self):
        pods = {"items": [pod(), pod(), pod(ready=False), pod(terminating=True), pod(ready=False, terminating=True)]}
        self.assertEqual(cluster.count_pods(pods), (2, 1, 2))

    def test_finished_pods_are_not_counted(self):
        self.assertEqual(cluster.count_pods({"items": [pod(phase="Succeeded"), pod(phase="Failed"), pod()]}), (1, 0, 0))

    def test_no_pods_is_zeros(self):
        self.assertEqual(cluster.count_pods({}), (0, 0, 0))


class SampleTests(unittest.TestCase):
    def test_a_sample_reads_pods_the_deployment_and_prometheus(self):
        fake = FakeKubectl(pods=[pod(), pod(ready=False)], replicas=3, running=5.0, waiting=2.0)
        s = cluster.take_sample(fake, now=lambda: 100.0)
        self.assertEqual((s.t, s.ready, s.pending, s.terminating, s.desired, s.running, s.waiting), (100.0, 1, 1, 0, 3, 5.0, 2.0))

    def test_prometheus_being_down_leaves_the_queue_unknown_but_the_pods_known(self):
        s = cluster.take_sample(FakeKubectl(pods=[pod()], prometheus_down=True))
        self.assertEqual((s.ready, s.running, s.waiting), (1, None, None))

    def test_an_empty_prometheus_result_is_zero(self):
        fake = FakeKubectl()
        fake.__class__ = type("Empty", (FakeKubectl,), {"__call__": lambda self, args, input=None:
                              json.dumps({"data": {"result": []}}) if args[:2] == ["get", "--raw"] else FakeKubectl.__call__(self, args, input)})
        self.assertEqual(cluster.prometheus_value(fake, "sum(x)"), 0.0)


class CollectorTests(unittest.TestCase):
    def test_it_samples_until_stopped(self):
        collector = cluster.Collector(FakeKubectl(pods=[pod()]), period_s=0.05).start()
        time.sleep(0.4)
        samples = collector.stop()
        self.assertGreaterEqual(len(samples), 3)
        self.assertEqual(collector.failures, 0)

    def test_a_failing_sample_is_counted_and_the_loop_goes_on(self):
        fake = FakeKubectl(pods=[pod()])
        original = fake.__call__
        state = {"n": 0}

        def flaky(args, input=None):
            state["n"] += 1
            if state["n"] == 1:
                raise RuntimeError("kubectl get failed")
            return original(args, input)
        collector = cluster.Collector(flaky, period_s=0.05).start()
        time.sleep(0.4)
        samples = collector.stop()
        self.assertEqual(collector.failures, 1)
        self.assertGreaterEqual(len(samples), 2)


def ok(index, ttft, e2e=None, arrival=0.0):
    return Result(index, arrival, 0.0, 100, 10, 200, ttft, e2e if e2e is not None else ttft + 1, 10, 100, 10)


def failed(index, arrival=0.0):
    return Result(index, arrival, 0.0, 100, 10, 0, None, 3.0, 0, error="timeout")


def sample(t, ready, pending=0, terminating=0, desired=None, waiting=0.0):
    return cluster.Sample(t, ready, pending, terminating, ready + pending if desired is None else desired, 0.0, waiting)


class BuildRunTests(unittest.TestCase):
    def setUp(self):
        self.w = tiny_workload(duration=60, slo=2.0)
        self.trace = [Request(0, 5.0, 100, 10), Request(1, 6.0, 100, 10), Request(2, 7.0, 100, 10)]

    def build(self, results, samples, start=1000.0):
        return cluster.build_run("p", self.w, self.trace, results, samples, start)

    def test_a_failed_request_misses_the_objective_and_stays_in_the_totals(self):
        run = self.build([ok(0, 0.5), ok(1, 1.5), failed(2)], [sample(1000, 2), sample(1030, 2), sample(1060, 2)])
        s = summarize(run, self.w)
        self.assertEqual(s["requests"], 3)
        self.assertAlmostEqual(s["goodput"], 2 / 3)
        self.assertEqual(run.ttft[2], cluster.FAILED_LATENCY_S)

    def test_cost_is_pods_that_exist_integrated_over_the_workloads_duration(self):
        # 2 pods for 30 s, then 5 (3 of them starting) for 30 s, sampled at the start, the middle and the end.
        run = self.build([ok(0, 0.1), ok(1, 0.1), ok(2, 0.1)],
                         [sample(1000, 2), sample(1030, 2, pending=3), sample(1060, 5)])
        self.assertAlmostEqual(run.replica_seconds, 2 * 30 + 5 * 30)

    def test_terminating_pods_still_cost_until_they_are_gone(self):
        run = self.build([ok(0, 0.1)] * 3, [sample(1000, 4), sample(1030, 2, terminating=2), sample(1060, 2)])
        self.assertAlmostEqual(run.replica_seconds, 4 * 30 + 4 * 30)

    def test_the_last_sample_holds_to_the_end_of_the_workload(self):
        run = self.build([ok(0, 0.1)] * 3, [sample(1000, 3), sample(1020, 3)])
        self.assertAlmostEqual(run.replica_seconds, 3 * 60)

    def test_samples_after_the_workload_ends_do_not_add_cost(self):
        run = self.build([ok(0, 0.1)] * 3, [sample(1000, 3), sample(1060, 3), sample(1090, 20)])
        self.assertAlmostEqual(run.replica_seconds, 3 * 60)

    def test_events_are_the_changes_in_the_desired_count_and_peak_counts_every_pod(self):
        run = self.build([ok(0, 0.1)] * 3, [sample(1000, 2), sample(1015, 2, desired=6), sample(1045, 6), sample(1050, 6, desired=4)])
        self.assertEqual(run.events, [(15.0, 4), (50.0, -2)])
        self.assertEqual(run.peak_replicas, 6)

    def test_the_queue_comes_from_the_waiting_samples(self):
        run = self.build([ok(0, 0.1)] * 3, [sample(1000, 2, waiting=10), sample(1020, 2, waiting=250), sample(1040, 2, waiting=3)])
        self.assertEqual(run.max_queue, 250)
        self.assertEqual([row[4] for row in run.timeline], [10, 250, 3])

    def test_it_summarises_with_the_same_function_as_the_simulation(self):
        run = self.build([ok(0, 0.2), ok(1, 3.0), ok(2, 0.4)], [sample(1000, 2), sample(1060, 2)])
        s = summarize(run, self.w)
        self.assertEqual(set(s), {"requests", "ttft_p50_ms", "ttft_p95_ms", "ttft_p99_ms", "latency_p95_s", "goodput",
                                  "unhealthy_s", "replica_seconds", "mean_replicas", "peak_replicas", "max_queue",
                                  "scale_ups", "scale_downs", "flaps", "replica_seconds_per_good_request"})
        self.assertAlmostEqual(s["ttft_p50_ms"], 400)
        self.assertEqual(s["mean_replicas"], 2.0)


class JobTests(unittest.TestCase):
    def runner_for(self, states):
        states = list(states)

        def runner(args, input=None):
            return json.dumps({"status": states.pop(0) if len(states) > 1 else states[0]})
        return runner

    def test_the_job_state_is_read_from_its_status(self):
        self.assertEqual(cluster.job_state(self.runner_for([{"succeeded": 1}])), "succeeded")
        self.assertEqual(cluster.job_state(self.runner_for([{"failed": 1}])), "failed")
        self.assertEqual(cluster.job_state(self.runner_for([{"active": 1}])), "running")

    def test_waiting_returns_when_the_job_finishes(self):
        runner = self.runner_for([{"active": 1}, {"active": 1}, {"succeeded": 1}])
        self.assertEqual(cluster.wait_for_job(runner, 100, sleep=lambda s: None), "succeeded")

    def test_waiting_gives_up_at_the_deadline(self):
        clock = iter([0.0, 5.0, 11.0, 20.0, 30.0])
        with self.assertRaisesRegex(RuntimeError, "did not finish"):
            cluster.wait_for_job(self.runner_for([{"active": 1}]), 10, sleep=lambda s: None, clock=lambda: next(clock))


class ClientOutputTests(unittest.TestCase):
    def test_the_last_json_line_is_the_result(self):
        r = ok(0, 0.5).to_dict()
        log = "replaying 1 requests\n" + json.dumps({"start_epoch": 1234.5, "results": [r]}) + "\n"
        start, results = cluster.parse_client_output(log)
        self.assertEqual(start, 1234.5)
        self.assertEqual(results[0].ttft_s, 0.5)

    def test_no_result_is_an_error(self):
        with self.assertRaisesRegex(RuntimeError, "no results"):
            cluster.parse_client_output("replaying\nboom\n")


if __name__ == "__main__":
    unittest.main()
