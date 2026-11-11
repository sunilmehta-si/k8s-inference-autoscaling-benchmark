import unittest

from inference_autoscaling_bench.policies import Bounds, Hpa, Observation, Static

BOUNDS = Bounds(min_replicas=2, max_replicas=32)


def obs(now=0.0, ready=4, pending=0, running=0, queued=0, slots=8, arrival_rate=0.0):
    return Observation(now, ready, pending, running, queued, slots, arrival_rate)


class RatioTests(unittest.TestCase):
    def test_a_metric_at_its_target_changes_nothing(self):
        self.assertEqual(Hpa("concurrency").decide(obs(running=24), BOUNDS), 4)

    def test_a_metric_inside_the_tolerance_changes_nothing(self):
        self.assertEqual(Hpa("concurrency").decide(obs(running=25), BOUNDS), 4)   # ratio 1.04

    def test_a_metric_above_its_target_scales_up_by_the_ratio(self):
        self.assertEqual(Hpa("concurrency").decide(obs(running=32, queued=4), BOUNDS), 6)  # 36/4/6 = 1.5, ceil(1.5*4)

    def test_a_metric_below_its_target_scales_down_by_the_ratio(self):
        self.assertEqual(Hpa("concurrency").decide(obs(ready=10, running=30), BOUNDS), 5)  # 30/10/6 = 0.5

    def test_each_signal_reads_its_own_metric(self):
        self.assertEqual(Hpa("utilization").decide(obs(running=24), BOUNDS), 5)    # 24/8 = 3 slots' worth, 3/4/0.6 = 1.25
        self.assertEqual(Hpa("queue").decide(obs(queued=8), BOUNDS), 8)             # 8/4/1 = 2
        self.assertEqual(Hpa("rps").decide(obs(arrival_rate=7.0), BOUNDS), 5)       # 7/4/1.4 = 1.25

    def test_an_idle_queue_asks_for_the_minimum(self):
        self.assertEqual(Hpa("queue").decide(obs(ready=4, queued=0), BOUNDS), 2)

    def test_a_custom_target_is_used(self):
        self.assertEqual(Hpa("concurrency", target=3.0).decide(obs(running=24), BOUNDS), 8)   # ratio 2, limited to +4

    def test_no_ready_pod_means_no_metric_and_no_change(self):
        self.assertIsNone(Hpa("concurrency").decide(obs(ready=0, pending=3, queued=50), BOUNDS))


class RecommendTests(unittest.TestCase):
    """recommend is steps 1 to 3 alone, so another policy can build on the HPA's own recommendation."""

    def test_it_is_the_count_decide_moves_to_before_bounds_windows_and_limits(self):
        for o in (obs(running=24), obs(running=32, queued=4), obs(ready=10, running=30), obs(ready=4, pending=2, running=60)):
            with self.subTest(obs=o):
                self.assertEqual(Hpa("concurrency").recommend(o), Hpa("concurrency").decide(o, BOUNDS))

    def test_it_is_unbounded_and_remembers_nothing(self):
        hpa = Hpa("concurrency")
        self.assertEqual(hpa.recommend(obs(running=600)), 100)
        self.assertEqual(hpa.recommend(obs(ready=10, running=0)), 0)
        self.assertEqual(len(hpa.history), 0)

    def test_no_metric_is_none(self):
        self.assertIsNone(Hpa("concurrency").recommend(obs(ready=0, pending=3, queued=50)))
        self.assertIsNone(Hpa("concurrency", external=True).recommend(obs(ready=0, pending=0)))


class StartingPodsTests(unittest.TestCase):
    def test_pods_still_starting_count_as_using_nothing_so_the_surge_is_not_ordered_twice(self):
        # 4 ready pods carry 48 requests (ratio 2) and 4 more are starting: with those counted the ratio is exactly 1.
        self.assertEqual(Hpa("concurrency").decide(obs(ready=4, pending=4, running=48), BOUNDS), 8)

    def test_a_surge_bigger_than_the_pods_on_the_way_asks_for_the_rest(self):
        # ratio 2.5 on the ready pods, 60/6/6 = 1.67 once the 2 starting pods are counted: ceil(1.67 * 6) = 10
        self.assertEqual(Hpa("concurrency").decide(obs(ready=4, pending=2, running=60), BOUNDS), 10)

    def test_pending_pods_do_not_stop_a_scale_down(self):
        self.assertEqual(Hpa("concurrency").decide(obs(ready=10, pending=2, running=30), BOUNDS), 5)



class ExternalMetricTests(unittest.TestCase):
    """KEDA's autoscaler reads the sum over the pods as an external metric with a target per pod."""

    def test_away_from_starting_pods_it_decides_as_the_pods_metric_does(self):
        for o in (obs(running=24), obs(running=25), obs(running=32, queued=4), obs(ready=10, running=30), obs(queued=8)):
            with self.subTest(obs=o):
                self.assertEqual(Hpa("concurrency", external=True).decide(o, BOUNDS), Hpa("concurrency").decide(o, BOUNDS))

    def test_starting_pods_count_in_the_average_before_the_tolerance(self):
        # 27 requests on 4 ready pods is 1.125 of the target, outside the tolerance; with the 2 starting pods counted the
        # pods' metric crosses 1 and holds at 6. The external metric averages over all 6 from the start (0.75) and
        # recommends ceil(27 / 6) = 5, which the scale-down window then holds off.
        self.assertEqual(Hpa("concurrency").decide(obs(ready=4, pending=2, running=27), BOUNDS), 6)
        self.assertEqual(Hpa("concurrency", external=True).decide(obs(ready=4, pending=2, running=27), BOUNDS), 5)

    def test_a_surge_asks_for_the_sum_over_the_target(self):
        self.assertEqual(Hpa("concurrency", external=True).decide(obs(ready=4, pending=2, running=60), BOUNDS), 10)

    def test_no_ready_pod_is_needed_for_a_decision(self):
        # The pods' metric has no value without a ready pod; the sum KEDA reads is there regardless.
        self.assertIsNone(Hpa("concurrency").decide(obs(ready=0, pending=3, queued=50), BOUNDS))
        self.assertEqual(Hpa("concurrency", external=True).decide(obs(ready=0, pending=3, queued=50), BOUNDS), 7)

    def test_it_is_named_for_keda(self):
        self.assertEqual(Hpa("queue", external=True).name, "keda-queue")

class LimitTests(unittest.TestCase):
    def test_scaling_up_is_limited_to_four_pods_or_doubling(self):
        self.assertEqual(Hpa("concurrency").decide(obs(ready=2, running=200), BOUNDS), 6)      # max(2 + 4, 2 * 2)
        self.assertEqual(Hpa("concurrency").decide(obs(ready=10, running=2000), BOUNDS), 20)   # max(10 + 4, 10 * 2)

    def test_the_bounds_clamp_the_count(self):
        self.assertEqual(Hpa("concurrency").decide(obs(ready=30, running=2000), BOUNDS), 32)
        self.assertEqual(Hpa("concurrency").decide(obs(ready=3, running=0), BOUNDS), 2)

    def test_the_limit_can_be_changed(self):
        self.assertEqual(Hpa("concurrency", up_pods=1, up_percent=0).decide(obs(ready=4, running=200), BOUNDS), 5)


class StabilizationTests(unittest.TestCase):
    def test_scaling_down_waits_for_the_highest_recommendation_of_the_window_to_age_out(self):
        policy = Hpa("concurrency", down_window_s=300)
        self.assertEqual(policy.decide(obs(now=0, ready=10, running=60), BOUNDS), 10)   # at target: recommends 10
        for now in range(15, 300, 15):
            self.assertEqual(policy.decide(obs(now=now, ready=10, running=6), BOUNDS), 10, now)
        self.assertEqual(policy.decide(obs(now=300, ready=10, running=6), BOUNDS), 10)  # the 10 of t=0 is still in the window
        self.assertEqual(policy.decide(obs(now=315, ready=10, running=6), BOUNDS), 2)   # and now it is not

    def test_a_shorter_window_releases_pods_sooner(self):
        policy = Hpa("concurrency", down_window_s=60)
        policy.decide(obs(now=0, ready=10, running=60), BOUNDS)
        results = {now: policy.decide(obs(now=now, ready=10, running=6), BOUNDS) for now in range(15, 90, 15)}
        self.assertEqual(results[60], 10)
        self.assertEqual(results[75], 2)

    def test_scaling_up_is_not_delayed_by_default(self):
        policy = Hpa("concurrency")
        policy.decide(obs(now=0, ready=4, running=0), BOUNDS)
        self.assertEqual(policy.decide(obs(now=15, ready=4, running=36), BOUNDS), 6)

    def test_an_up_window_makes_scaling_up_wait_for_a_steady_recommendation(self):
        policy = Hpa("concurrency", up_window_s=60)
        policy.decide(obs(now=0, ready=4, running=24), BOUNDS)           # recommends 4
        self.assertEqual(policy.decide(obs(now=15, ready=4, running=36), BOUNDS), 4)   # 6 wanted, 4 in the window
        results = [policy.decide(obs(now=now, ready=4, running=36), BOUNDS) for now in (30, 45, 60, 75)]
        self.assertEqual(results, [4, 4, 4, 6])


class ConstructionTests(unittest.TestCase):
    def test_static_policies_hold_their_size(self):
        policy = Static(12)
        self.assertEqual(policy.initial(BOUNDS), 12)
        self.assertEqual(policy.name, "static-12")
        self.assertIsNone(policy.decide(obs(running=999), BOUNDS))

    def test_hpa_starts_at_the_minimum(self):
        self.assertEqual(Hpa("queue").initial(BOUNDS), 2)

    def test_bad_arguments_are_refused(self):
        with self.assertRaises(ValueError):
            Hpa("gpu-temperature")
        with self.assertRaises(ValueError):
            Hpa("queue", target=0)


if __name__ == "__main__":
    unittest.main()
