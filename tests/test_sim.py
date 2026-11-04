import unittest
from pathlib import Path

from inference_autoscaling_bench import sim, workload
from inference_autoscaling_bench.policies import Bounds, Hpa, Static
from tests.helpers import Scripted, tiny_workload, trace

ROOT = Path(__file__).resolve().parent.parent
ONE = Bounds(min_replicas=1, max_replicas=32)


def run(rows, policy, replica=sim.Replica(), duration=60):
    return sim.simulate(trace(*rows), tiny_workload(duration), policy, replica, ONE)


class ServiceTimeTests(unittest.TestCase):
    def test_one_request_on_an_idle_pod_takes_its_prefill_and_decode_time(self):
        r = run([(1.0, 400, 10)], Static(1))
        self.assertAlmostEqual(r.wait[0], 0.0)
        self.assertAlmostEqual(r.ttft[0], 0.1 + 0.02)          # 400 / 4000 s of prefill, then the first token
        self.assertAlmostEqual(r.latency[0], 0.1 + 10 * 0.02)

    def test_a_request_waits_for_a_slot(self):
        r = run([(1.0, 400, 10), (1.0, 400, 10)], Static(1), sim.Replica(slots=1))
        self.assertAlmostEqual(r.wait[1], 0.3)                  # the first one's whole service time
        self.assertAlmostEqual(r.ttft[1], 0.3 + 0.1 + 0.02)

    def test_sharing_a_pod_slows_a_request_down(self):
        r = run([(1.0, 400, 10), (1.0, 400, 10)], Static(1), sim.Replica(slots=2))
        self.assertAlmostEqual(r.ttft[0], 0.12)
        self.assertAlmostEqual(r.ttft[1], 0.1 * (1 + 0.5 * 0.5) + 0.02 * (1 + 0.6 * 0.5))

    def test_a_request_goes_to_the_least_loaded_pod(self):
        r = run([(1.0, 400, 10), (1.0, 400, 10)], Static(2), sim.Replica(slots=2))
        self.assertAlmostEqual(r.ttft[1], 0.12)                 # its own pod, so no slowdown


class ScalingTests(unittest.TestCase):
    def test_a_new_pod_serves_nothing_until_its_startup_has_passed(self):
        # One slot, busy for 40 s. A pod ordered at the t=15 sync is ready at t=25, so a request at t=20 waits for it.
        r = run([(1.0, 400, 2000), (20.0, 400, 10)], Scripted(1, {15.0: 2}), sim.Replica(slots=1, startup_s=10))
        self.assertAlmostEqual(r.wait[1], 5.0)

    def test_without_a_new_pod_the_request_waits_for_the_busy_one(self):
        r = run([(1.0, 400, 2000), (20.0, 400, 10)], Static(1), sim.Replica(slots=1, startup_s=10))
        self.assertAlmostEqual(r.wait[1], 1.0 + 0.1 + 2000 * 0.02 - 20.0)

    def test_scaling_up_costs_from_creation_not_from_readiness(self):
        r = run([(1.0, 400, 10)], Scripted(1, {15.0: 3}), sim.Replica(startup_s=30))
        self.assertAlmostEqual(r.replica_seconds, 60 + 2 * 45)
        self.assertEqual(r.events, [(15.0, 2)])
        self.assertEqual(r.peak_replicas, 3)

    def test_a_static_deployment_costs_its_size_times_the_duration(self):
        self.assertAlmostEqual(run([(1.0, 400, 10)], Static(3), duration=60).replica_seconds, 180)

    def test_pods_still_starting_are_removed_first_and_cost_only_while_they_existed(self):
        r = run([(1.0, 400, 10)], Scripted(1, {15.0: 3, 30.0: 1}), sim.Replica(startup_s=100))
        self.assertAlmostEqual(r.replica_seconds, 60 + 2 * 15)
        self.assertEqual([change for _, change in r.events], [2, -2])

    def test_a_pod_asked_to_leave_finishes_its_requests_and_then_stops_costing(self):
        # Two one-slot pods, each busy for ~20 s. At t=15 one is removed: the newer one, holding the later request.
        r = run([(1.0, 400, 1000), (2.0, 400, 1000)], Scripted(2, {15.0: 1}), sim.Replica(slots=1), duration=60)
        self.assertAlmostEqual(r.latency[0], 0.1 + 20.0)
        self.assertAlmostEqual(r.latency[1], 0.1 + 20.0)        # not dropped, not slowed
        self.assertAlmostEqual(r.replica_seconds, 60 + (2.0 + 0.1 + 20.0))   # the removed pod lived until its request ended

    def test_an_idle_pod_is_removed_at_once(self):
        r = run([(1.0, 400, 10)], Scripted(3, {15.0: 1}), sim.Replica(slots=1), duration=60)
        self.assertAlmostEqual(r.replica_seconds, 60 + 2 * 15)

    def test_the_first_sync_is_one_period_after_the_start(self):
        r = run([(1.0, 400, 10)], Scripted(1, {0.0: 5}))
        self.assertEqual(r.events, [])

    def test_a_shorter_sync_period_lets_the_autoscaler_act_sooner(self):
        # Asked at t=5 for a second pod that starts in 10 s, a request at t=20 finds it ready; at a 15 s period it would
        # be asked at t=15 and ready at 25.
        rows = [(1.0, 400, 2000), (20.0, 400, 10)]
        fast = sim.simulate(trace(*rows), tiny_workload(60), Scripted(1, {5.0: 2}), sim.Replica(slots=1, startup_s=10), ONE, 5.0)
        slow = sim.simulate(trace(*rows), tiny_workload(60), Scripted(1, {15.0: 2}), sim.Replica(slots=1, startup_s=10), ONE, 15.0)
        self.assertAlmostEqual(fast.wait[1], 0.0)
        self.assertAlmostEqual(slow.wait[1], 5.0)
        self.assertEqual([row[0] for row in fast.timeline][:4], [0.0, 5.0, 10.0, 15.0])

    def test_the_timeline_has_one_row_per_sync_period(self):
        r = run([(1.0, 400, 10)], Static(1), duration=60)
        self.assertEqual([row[0] for row in r.timeline], [0.0, 15.0, 30.0, 45.0, 60.0])

    def test_requests_that_can_never_start_are_an_error_not_a_zero(self):
        with self.assertRaises(RuntimeError):
            run([(1.0, 400, 10)], Static(0))


class WholeRunTests(unittest.TestCase):
    def setUp(self):
        self.smoke = workload.load(ROOT / "workloads/smoke.json")
        self.trace = workload.generate(self.smoke, 1)

    def test_every_request_is_served_and_none_is_faster_than_physics(self):
        r = sim.simulate(self.trace, self.smoke, Hpa("concurrency"))
        self.assertEqual(len(r.ttft), len(self.trace))
        for req, ttft, latency, wait in zip(self.trace, r.ttft, r.latency, r.wait):
            self.assertGreater(ttft, req.prompt_tokens / 4000)
            self.assertGreaterEqual(latency, ttft - 1e-9)
            self.assertGreaterEqual(wait, 0)

    def test_the_same_inputs_give_the_same_run(self):
        a = sim.simulate(self.trace, self.smoke, Hpa("queue"))
        b = sim.simulate(self.trace, self.smoke, Hpa("queue"))
        self.assertEqual((a.ttft, a.events, a.timeline, a.replica_seconds), (b.ttft, b.events, b.timeline, b.replica_seconds))

    def test_the_peak_stays_inside_the_bounds(self):
        r = sim.simulate(self.trace, self.smoke, Hpa("concurrency"))
        self.assertGreaterEqual(r.peak_replicas, Bounds().min_replicas)
        self.assertLessEqual(r.peak_replicas, Bounds().max_replicas)

    def test_a_bigger_fixed_pool_is_never_slower_on_the_same_trace(self):
        small = sim.simulate(self.trace, self.smoke, Static(2))
        big = sim.simulate(self.trace, self.smoke, Static(8))
        self.assertLessEqual(sum(big.wait), sum(small.wait))

    def test_a_bad_replica_is_refused(self):
        with self.assertRaises(ValueError):
            sim.Replica(slots=0)


if __name__ == "__main__":
    unittest.main()
