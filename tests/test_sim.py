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


class PodQueueTests(unittest.TestCase):
    """With pod_queues each request is sent to a ready pod when it arrives and waits in that pod's own queue."""

    def run_pod(self, rows, policy, replica, seed=0):
        return sim.simulate(trace(*rows), tiny_workload(60), policy, replica, ONE, pod_queues=True, route_seed=seed)

    def test_a_request_alone_is_served_exactly_as_with_one_queue(self):
        a = run([(1.0, 400, 10)], Static(2))
        b = self.run_pod([(1.0, 400, 10)], Static(2), sim.Replica())
        self.assertEqual((a.wait, a.ttft, a.latency), (b.wait, b.ttft, b.latency))

    def test_work_queued_on_a_pod_does_not_move_to_a_pod_that_becomes_ready_later(self):
        # One busy slot, a long queue behind it, then a second pod ready at t=25. With one queue the new pod takes the
        # waiting requests at once; with per-pod queues they stay where they were sent.
        rows = [(1.0, 400, 2000)] + [(2.0 + i * 0.01, 400, 10) for i in range(4)]
        script, replica = {15.0: 2}, sim.Replica(slots=1, startup_s=10)
        central = sim.simulate(trace(*rows), tiny_workload(60), Scripted(1, script), replica, ONE)
        per_pod = self.run_pod(rows, Scripted(1, script), replica)
        self.assertLess(central.wait[1], 24.0)         # the new pod starts the first of them at t=25
        self.assertGreater(per_pod.wait[1], 38.0)      # it waits for the busy pod: 1 + 0.1 + 2000 * 0.02 - 2
        self.assertEqual(per_pod.max_queue, central.max_queue)

    def test_the_same_seed_gives_the_same_run_and_the_route_is_random_across_ready_pods(self):
        rows = [(1.0 + i * 0.001, 400, 100) for i in range(40)]
        waits = lambda seed: self.run_pod(rows, Static(4), sim.Replica(slots=2), seed).wait
        self.assertEqual(waits(3), waits(3))
        self.assertNotEqual(waits(3), waits(4))

    def test_every_request_is_served_and_cost_is_unchanged_by_the_queue_model(self):
        rows = [(1.0 + i * 0.5, 400, 40) for i in range(60)]
        a = run(rows, Static(3), sim.Replica(slots=2), duration=90)
        b = sim.simulate(trace(*rows), tiny_workload(90), Static(3), sim.Replica(slots=2), ONE, pod_queues=True)
        self.assertEqual(a.replica_seconds, b.replica_seconds)
        self.assertEqual(len(b.wait), 60)
        self.assertTrue(all(t > 0 for t in b.ttft))

    def test_a_draining_pod_finishes_the_requests_already_queued_on_it(self):
        rows = [(1.0, 400, 1000)] + [(2.0, 400, 10)] * 6
        scale = Scripted(4, {15.0: 1})
        r = self.run_pod(rows, scale, sim.Replica(slots=1, startup_s=5), seed=1)
        self.assertEqual(len(r.latency), 7)
        self.assertTrue(all(x > 0 for x in r.latency))


class Recorder(Static):
    """A fixed pool that writes down what the autoscaler saw at every sync."""

    def __init__(self, replicas):
        super().__init__(replicas)
        self.seen = []

    def decide(self, obs, bounds):
        self.seen.append((obs.now, obs.ready, obs.running + obs.queued))
        return None


class MetricsLagTests(unittest.TestCase):
    """With metrics_lag_s the autoscaler acts on the signal from the latest sync at least that long ago."""

    ROWS = [(20.0 + i * 0.01, 400, 2000) for i in range(6)]   # six long requests arrive between the syncs at 15 and 30

    def seen(self, lag):
        policy = Recorder(2)
        sim.simulate(trace(*self.ROWS), tiny_workload(90), policy, sim.Replica(), ONE, metrics_lag_s=lag)
        return {t: load for t, _, load in policy.seen}

    def test_without_lag_the_load_is_seen_at_the_first_sync_after_it_arrives(self):
        self.assertEqual((self.seen(0)[15.0], self.seen(0)[30.0]), (0, 6))

    def test_a_lag_of_one_period_shows_it_one_sync_later(self):
        seen = self.seen(15)
        self.assertEqual((seen[30.0], seen[45.0]), (0, 6))

    def test_a_lag_between_syncs_rounds_back_to_the_older_sample(self):
        seen = self.seen(20)
        self.assertEqual((seen[30.0], seen[45.0], seen[60.0]), (0, 0, 6))

    def test_before_the_start_the_autoscaler_sees_the_start(self):
        self.assertEqual(self.seen(60)[15.0], 0)

    def test_pod_counts_are_not_lagged(self):
        policy = Recorder(3)
        sim.simulate(trace(*self.ROWS), tiny_workload(90), policy, sim.Replica(), ONE, metrics_lag_s=45)
        self.assertTrue(all(ready == 3 for _, ready, _ in policy.seen))

    def test_no_lag_is_the_default(self):
        burst = workload.load(ROOT / "workloads/burst.json")
        reqs = workload.generate(burst, 1)
        a = sim.simulate(reqs, burst, Hpa("concurrency"), sim.Replica(), Bounds())
        b = sim.simulate(reqs, burst, Hpa("concurrency"), sim.Replica(), Bounds(), metrics_lag_s=0)
        self.assertEqual((a.ttft, a.events), (b.ttft, b.events))

    def test_lag_delays_the_first_scale_up_on_a_burst(self):
        burst = workload.load(ROOT / "workloads/burst.json")
        reqs = workload.generate(burst, 1)
        first = lambda lag: sim.simulate(reqs, burst, Hpa("concurrency"), sim.Replica(), Bounds(),
                                         metrics_lag_s=lag).events[0][0]
        self.assertGreater(first(30), first(0))

    def test_a_negative_lag_is_refused(self):
        with self.assertRaisesRegex(ValueError, "negative"):
            sim.simulate(trace(*self.ROWS), tiny_workload(90), Static(1), sim.Replica(), ONE, metrics_lag_s=-1)
