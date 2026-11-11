import unittest
from pathlib import Path

from inference_autoscaling_bench import experiment, spec, workload
from inference_autoscaling_bench.policies import Hpa, Predictive, Static
from tests.helpers import tiny_workload


class ParseTests(unittest.TestCase):
    def test_a_static_pool(self):
        s = spec.parse("static-24")
        self.assertEqual((s.label, s.replica.startup_s), ("static-24", 45.0))
        self.assertIsInstance(s.make(), Static)
        self.assertEqual(s.make().replicas, 24)

    def test_an_hpa_with_every_default(self):
        policy = spec.parse("hpa-concurrency").make()
        self.assertIsInstance(policy, Hpa)
        self.assertEqual((policy.signal, policy.target, policy.down_window_s), ("concurrency", 6.0, 300.0))

    def test_options_reach_the_hpa_and_the_replica(self):
        s = spec.parse("hpa-queue:target=2,down=60,up_pods=8,startup=120")
        policy = s.make()
        self.assertEqual((policy.target, policy.down_window_s, policy.up_pods), (2.0, 60.0, 8))
        self.assertEqual(s.replica.startup_s, 120.0)

    def test_the_fewest_pods_can_be_set_per_policy(self):
        self.assertEqual(spec.parse("hpa-concurrency:min=6").min_replicas, 6)
        self.assertIsNone(spec.parse("hpa-concurrency").min_replicas)
        self.assertEqual(spec.parse("warm=hpa-queue:min=4,startup=10").min_replicas, 4)
        with self.assertRaisesRegex(ValueError, "at least 1"):
            spec.parse("hpa-concurrency:min=0")

    def test_the_decision_period_can_be_set_per_policy(self):
        self.assertEqual(spec.parse("hpa-queue").sync_s, 15.0)
        self.assertEqual(spec.parse("hpa-queue:sync=5").sync_s, 5.0)
        with self.assertRaisesRegex(ValueError, "positive"):
            spec.parse("hpa-queue:sync=0")

    def test_a_label_names_the_policy_in_results(self):
        s = spec.parse("slow=hpa-rps:startup=120")
        self.assertEqual((s.label, s.make().name, s.replica.startup_s), ("slow", "slow", 120.0))

    def test_an_unlabelled_variant_is_labelled_by_its_text(self):
        self.assertEqual(spec.parse("hpa-queue:target=2").label, "hpa-queue:target=2")

    def test_every_make_is_a_fresh_policy(self):
        s = spec.parse("hpa-queue")
        self.assertIsNot(s.make(), s.make())

    def test_bad_specs_are_refused_with_a_reason(self):
        for bad, reason in [("hpa-gpu", "unknown policy"), ("static-0", "at least one"), ("static-x", "pool size"),
                            ("hpa-queue:nope=1", "unknown option"), ("hpa-queue:target", "key=value"),
                            ("static-4:target=2", "no options"), ("hpa-queue:target=abc", "must be a number"),
                            ("burst", "unknown policy")]:
            with self.subTest(spec=bad), self.assertRaisesRegex(ValueError, reason):
                spec.parse(bad)



class KedaSpecTests(unittest.TestCase):
    def test_keda_is_the_hpa_reading_an_external_metric(self):
        policy = spec.parse("keda-concurrency").make()
        self.assertIsInstance(policy, Hpa)
        self.assertEqual((policy.signal, policy.target, policy.external, policy.name), ("concurrency", 6.0, True, "keda-concurrency"))
        self.assertFalse(spec.parse("hpa-concurrency").make().external)

    def test_keda_takes_the_hpas_options(self):
        s = spec.parse("keda-queue:down=60,startup=20,route=pod,scrape=15")
        policy = s.make()
        self.assertEqual((policy.down_window_s, s.replica.startup_s, s.pod_queues, s.scrape_s), (60.0, 20.0, True, 15.0))

    def test_external_is_the_same_controller_as_keda_under_its_own_label(self):
        external, keda = spec.parse("external-utilization").make(), spec.parse("keda-utilization").make()
        self.assertEqual((external.signal, external.target, external.external, external.name), ("utilization", 0.6, True, "external-utilization"))
        self.assertEqual((keda.signal, keda.target, keda.external), (external.signal, external.target, external.external))

    def test_an_unknown_keda_signal_is_refused(self):
        with self.assertRaisesRegex(ValueError, r"keda-<"):
            spec.parse("keda-gpu")

class PredictSpecTests(unittest.TestCase):
    def test_predict_is_the_predictive_policy_on_a_signal(self):
        policy = spec.parse("predict-concurrency").make()
        self.assertIsInstance(policy, Predictive)
        self.assertEqual((policy.signal, policy.target, policy.name, policy.floor), ("concurrency", 6.0, "predict-concurrency", True))

    def test_it_looks_one_pod_startup_ahead_by_default(self):
        self.assertEqual(spec.parse("predict-rps").make().horizon_s, 45.0)
        self.assertEqual(spec.parse("predict-rps:startup=120").make().horizon_s, 120.0)

    def test_it_takes_the_hpas_options(self):
        s = spec.parse("ahead=predict-queue:target=2,down=60,up_pods=8,min=6")
        policy = s.make()
        self.assertEqual((policy.target, policy.down_window_s, policy.up_pods, policy.name, s.min_replicas), (2.0, 60.0, 8, "ahead", 6))

    def test_the_horizon_and_the_forecasters_weights_can_be_set(self):
        policy = spec.parse("predict-rps:horizon=90,alpha=0.3,beta=0.1").make()
        self.assertEqual((policy.horizon_s, policy.forecaster.alpha, policy.forecaster.beta), (90.0, 0.3, 0.1))
        self.assertEqual(spec.parse("predict-rps:startup=120,horizon=30").make().horizon_s, 30.0)
        self.assertEqual(spec.parse("predict-rps:horizon=0").make().horizon_s, 0.0)

    def test_the_defaults_are_the_ones_chosen_before_any_dataset(self):
        policy = spec.parse("predict-concurrency").make()
        self.assertEqual((policy.forecaster.alpha, policy.forecaster.beta), (0.5, 0.3))

    def test_a_bad_horizon_alpha_or_beta_is_refused_when_the_spec_is_read(self):
        for text, reason in (("predict-rps:horizon=-5", "horizon"), ("predict-rps:alpha=0", "alpha"),
                             ("predict-rps:alpha=2", "alpha"), ("predict-rps:beta=-1", "beta"),
                             ("predict-rps:horizon=soon", "must be a number")):
            with self.subTest(text=text), self.assertRaisesRegex(ValueError, reason):
                spec.parse(text)

    def test_forecast_options_belong_to_predict_only(self):
        for text in ("hpa-rps:horizon=60", "keda-rps:alpha=0.5", "static-4:beta=0.2"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                spec.parse(text)

    def test_every_make_is_a_fresh_forecaster(self):
        s = spec.parse("predict-rps")
        self.assertIsNot(s.make().forecaster, s.make().forecaster)

    def test_an_unknown_signal_names_the_predict_family(self):
        with self.assertRaisesRegex(ValueError, r"predict-<"):
            spec.parse("predict-gpu")


class MatrixTests(unittest.TestCase):
    def test_every_policy_runs_on_every_seed_and_shares_the_trace(self):
        w = tiny_workload()
        rows, kept = experiment.run_matrix(w, [spec.parse("static-2"), spec.parse("hpa-queue")], [1, 2], keep_runs_for=1)
        self.assertEqual([(r["policy"], r["seed"]) for r in rows],
                         [("static-2", 1), ("hpa-queue", 1), ("static-2", 2), ("hpa-queue", 2)])
        self.assertEqual(rows[0]["requests"], rows[1]["requests"])   # one trace per seed, whatever the policy
        self.assertNotEqual(rows[0]["requests"], rows[2]["requests"])
        self.assertEqual(sorted(kept), ["hpa-queue", "static-2"])

    def test_a_policy_with_its_own_minimum_starts_with_that_many_pods(self):
        w = tiny_workload()
        rows, _ = experiment.run_matrix(w, [spec.parse("hpa-queue:min=5"), spec.parse("hpa-queue")], [1])
        self.assertEqual([r["peak_replicas"] for r in rows], [5, 2])

    def test_two_policies_with_one_label_are_refused(self):
        with self.assertRaises(ValueError):
            experiment.run_matrix(tiny_workload(), [spec.parse("static-2"), spec.parse("static-2")], [1])


if __name__ == "__main__":
    unittest.main()


class RouteTests(unittest.TestCase):
    def test_route_pod_turns_on_per_pod_queues_and_central_is_the_default(self):
        self.assertFalse(spec.parse("hpa-concurrency").pod_queues)
        self.assertFalse(spec.parse("hpa-concurrency:route=central").pod_queues)
        self.assertTrue(spec.parse("hpa-concurrency:route=pod").pod_queues)
        self.assertTrue(spec.parse("static-4:route=pod").pod_queues)

    def test_any_other_route_is_refused(self):
        with self.assertRaises(ValueError):
            spec.parse("hpa-concurrency:route=random")


class WithRouteTests(unittest.TestCase):
    def test_the_route_is_added_and_a_label_is_kept(self):
        for text, label in (("static-24", "static-24"), ("target-3=hpa-concurrency:target=3", "target-3"), ("limit=hpa-concurrency", "limit")):
            with self.subTest(text=text):
                s = spec.parse(spec.with_route(text, "pod"))
                self.assertTrue(s.pod_queues)
                self.assertEqual(s.label, label)

    def test_an_unlabelled_spec_with_options_keeps_them_and_a_route_already_set_is_refused(self):
        s = spec.parse(spec.with_route("hpa-queue:down=60", "pod"))
        self.assertTrue(s.pod_queues)
        with self.assertRaises(ValueError):
            spec.with_route("hpa-queue:route=central", "pod")


class LagTests(unittest.TestCase):
    def test_lag_is_parsed_for_an_hpa_and_a_static_pool(self):
        self.assertEqual(spec.parse("hpa-queue:lag=30").metrics_lag_s, 30.0)
        self.assertEqual(spec.parse("static-4:lag=15").metrics_lag_s, 15.0)

    def test_no_lag_is_the_default(self):
        self.assertEqual(spec.parse("hpa-queue").metrics_lag_s, 0.0)

    def test_a_negative_or_non_numeric_lag_is_refused(self):
        for text in ("hpa-queue:lag=-5", "hpa-queue:lag=soon"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                spec.parse(text)

    def test_the_matrix_passes_the_lag_to_the_simulation(self):
        w = workload.load(Path(__file__).resolve().parent.parent / "workloads/burst.json")
        rows, _ = experiment.run_matrix(w, [spec.parse("a=hpa-concurrency"), spec.parse("b=hpa-concurrency:lag=30")], [1])
        self.assertNotEqual(rows[0]["goodput"], rows[1]["goodput"])


class ScrapeOptionTests(unittest.TestCase):
    def test_scrape_is_parsed_for_an_hpa_and_a_static_pool(self):
        self.assertEqual(spec.parse("hpa-queue:scrape=15").scrape_s, 15.0)
        self.assertEqual(spec.parse("static-4:route=pod,scrape=15").scrape_s, 15.0)

    def test_no_scraping_is_the_default(self):
        self.assertEqual(spec.parse("hpa-queue").scrape_s, 0.0)
        self.assertEqual(spec.parse("hpa-queue:lag=30").scrape_s, 0.0)

    def test_a_non_positive_or_non_numeric_interval_is_refused(self):
        for text in ("hpa-queue:scrape=0", "hpa-queue:scrape=-5", "hpa-queue:scrape=often"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                spec.parse(text)

    def test_lag_and_scrape_together_are_refused(self):
        with self.assertRaisesRegex(ValueError, "not both"):
            spec.parse("hpa-queue:lag=30,scrape=15")

    def test_the_matrix_passes_the_interval_to_the_simulation(self):
        w = workload.load(Path(__file__).resolve().parent.parent / "workloads/burst.json")
        rows, _ = experiment.run_matrix(w, [spec.parse("a=hpa-concurrency:route=pod"), spec.parse("b=hpa-concurrency:route=pod,scrape=15")], [1])
        self.assertNotEqual(rows[0]["ttft_p95_ms"], rows[1]["ttft_p95_ms"])
