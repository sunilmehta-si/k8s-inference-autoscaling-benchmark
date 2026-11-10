"""The cluster files cannot be run in a unit test, so these hold them to what can be checked: pins, the refusal to touch
any other cluster, and that the pieces of the metrics path agree on names."""
import os
import re
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEPLOY = ROOT / "deploy"
SCRIPTS = ROOT / "scripts"


def versions() -> dict:
    out = {}
    for line in (DEPLOY / "versions.env").read_text().splitlines():
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            out[key] = value
    return out


class PinTests(unittest.TestCase):
    def test_every_image_is_pinned_by_digest(self):
        v = versions()
        for key in ("KIND_NODE_IMAGE", "SIM_IMAGE", "PROMETHEUS_IMAGE", "PROMETHEUS_ADAPTER_IMAGE", "PYTHON_IMAGE", "KEDA_IMAGE",
                    "KEDA_METRICS_APISERVER_IMAGE", "KEDA_ADMISSION_WEBHOOKS_IMAGE"):
            with self.subTest(image=key):
                self.assertRegex(v[key], r"@sha256:[0-9a-f]{64}$")

    def test_the_image_tags_agree_with_the_versions_beside_them(self):
        v = versions()
        self.assertIn(f":{v['PROMETHEUS_VERSION']}@", v["PROMETHEUS_IMAGE"])
        self.assertIn(f":{v['PROMETHEUS_ADAPTER_VERSION']}@", v["PROMETHEUS_ADAPTER_IMAGE"])
        for key in ("KEDA_IMAGE", "KEDA_METRICS_APISERVER_IMAGE", "KEDA_ADMISSION_WEBHOOKS_IMAGE"):
            with self.subTest(image=key):   # KEDA tags its images without the v its releases carry
                self.assertIn(f":{v['KEDA_VERSION'].removeprefix('v')}@", v[key])

    def test_every_download_has_a_checksum(self):
        for key in ("KIND_SHA256_LINUX_AMD64", "KEDA_MANIFEST_SHA256"):
            with self.subTest(download=key):
                self.assertRegex(versions()[key], r"^[0-9a-f]{64}$")

    def test_the_dockerfile_takes_its_base_from_the_pin(self):
        text = (ROOT / "Dockerfile").read_text()
        self.assertIn("ARG PYTHON_IMAGE", text)
        self.assertIn("FROM ${PYTHON_IMAGE}", text)
        self.assertIn("--build-arg \"PYTHON_IMAGE=${PYTHON_IMAGE}\"", (SCRIPTS / "build-client.sh").read_text())
        self.assertIn("USER 10001", text)

    def test_no_manifest_names_an_image_directly(self):
        for path in DEPLOY.rglob("*.yaml"):
            for line in path.read_text().splitlines():
                match = re.match(r"\s*image:\s*(\S+)", line)
                if match:
                    with self.subTest(file=path.name, image=match.group(1)):
                        self.assertRegex(match.group(1), r"^\$\{[A-Z_]+\}$")

    def test_every_variable_a_manifest_uses_is_one_its_script_substitutes(self):
        renders = {"servers.yaml": "deploy-servers.sh", "monitoring.yaml": "deploy-monitoring.sh"}
        for manifest, script in renders.items():
            used = set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", (DEPLOY / manifest).read_text()))
            listed = set(re.findall(r"\$\{([A-Z_]+)\}", re.search(r"envsubst '([^']*)'", (SCRIPTS / script).read_text()).group(1)))
            with self.subTest(manifest=manifest):
                self.assertEqual(used, listed)
        job = set(re.findall(r"\$\{([A-Z_]+)\}", (DEPLOY / "client.yaml").read_text()))
        filled = set(re.findall(r'replace\("\$\{([A-Z_]+)\}"', (ROOT / "inference_autoscaling_bench/cluster.py").read_text()))
        self.assertEqual(job, filled)
        hpa = set()
        for path in (DEPLOY / "hpa").glob("*.yaml"):
            hpa |= set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", path.read_text()))
        listed = set(re.findall(r"\$\{([A-Z_]+)\}", re.search(r"envsubst '([^']*)'", (SCRIPTS / "apply-hpa.sh").read_text()).group(1)))
        self.assertEqual(hpa, listed)
        keda = set()
        for path in (DEPLOY / "keda").glob("*.yaml"):
            keda |= set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", path.read_text()))
        listed = set(re.findall(r"\$\{([A-Z_]+)\}", re.search(r"envsubst '([^']*)'", (SCRIPTS / "apply-keda.sh").read_text()).group(1)))
        self.assertEqual(keda, listed)

    def test_keda_gets_the_same_defaults_as_the_hpa(self):
        def defaults(script):
            return re.search(r"export (MIN_REPLICAS=.*)", (SCRIPTS / script).read_text()).group(1)
        self.assertEqual(defaults("apply-keda.sh"), defaults("apply-hpa.sh"))

    def test_every_variable_substituted_is_defined_by_the_versions_or_the_script(self):
        v = versions()
        for script in ("deploy-servers.sh", "deploy-monitoring.sh"):
            text = (SCRIPTS / script).read_text()
            for name in re.findall(r"\$\{([A-Z_]+)\}", re.search(r"envsubst '([^']*)'", text).group(1)):
                with self.subTest(script=script, name=name):
                    self.assertTrue(name in v or re.search(rf"export {name}=", text), name)


class ContextGuardTests(unittest.TestCase):
    def run_guard(self, context: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "kubectl"
            fake.write_text(f'#!/bin/sh\n[ "$1 $2" = "config current-context" ] && echo "{context}"\n')
            fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
            return subprocess.run(["bash", "-c", f'. "{SCRIPTS}/lib.sh"; require_context; echo passed'],
                                  capture_output=True, text=True, env={**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}"})

    def test_a_real_clusters_context_is_refused(self):
        for context in ("gke_my-project_europe-west1_prod", "kind-irb", "docker-desktop", ""):
            with self.subTest(context=context):
                result = self.run_guard(context)
                self.assertEqual(result.returncode, 1)
                self.assertIn("refusing to run", result.stderr)
                self.assertNotIn("passed", result.stdout)

    def test_the_benchmarks_own_context_is_accepted(self):
        result = self.run_guard("kind-iab")
        self.assertEqual((result.returncode, result.stdout.strip()), (0, "passed"))

    def test_every_script_that_touches_the_cluster_checks_the_context(self):
        for script in SCRIPTS.glob("*.sh"):
            if script.name == "lib.sh":
                continue
            text = script.read_text()
            with self.subTest(script=script.name):
                self.assertIn('. "$(dirname "$0")/lib.sh"', text)
                self.assertIn("require_context", text)
                self.assertTrue(script.stat().st_mode & stat.S_IXUSR, "not executable")


class ManifestTests(unittest.TestCase):
    def test_namespaces_enforce_the_restricted_pod_security_standard(self):
        for name in ("servers.yaml", "monitoring.yaml"):
            self.assertIn("pod-security.kubernetes.io/enforce: restricted", (DEPLOY / name).read_text())
        # the load client runs in the iab namespace, so it must meet the same standard
        client = (DEPLOY / "client.yaml").read_text()
        for setting in ("runAsNonRoot: true", "allowPrivilegeEscalation: false", 'capabilities: {drop: ["ALL"]}',
                        "readOnlyRootFilesystem: true", "RuntimeDefault"):
            self.assertIn(setting, client)

    def test_every_container_drops_all_capabilities_and_blocks_escalation(self):
        for name in ("servers.yaml", "monitoring.yaml"):
            text = (DEPLOY / name).read_text()
            containers = len(re.findall(r"^\s+- name: [a-z-]+\n\s+image:", text, re.M))
            self.assertGreater(containers, 0)
            self.assertEqual(text.count("allowPrivilegeEscalation: false"), containers, name)
            self.assertEqual(text.count('capabilities: {drop: ["ALL"]}'), containers, name)

    def test_the_hpa_reads_a_metric_the_adapter_exposes_from_a_series_prometheus_records(self):
        monitoring = (DEPLOY / "monitoring.yaml").read_text()
        recorded = set(re.findall(r"record: iab_(\w+)", monitoring))
        exposed = set(re.search(r'iab_\(([a-z|]+)\)', monitoring).group(1).split("|"))
        self.assertEqual(recorded, exposed)
        for path in (DEPLOY / "hpa").glob("*.yaml"):
            metric = re.search(r"metric: \{name: (\w+)\}", path.read_text()).group(1)
            self.assertIn(metric, recorded)

    def test_no_role_grants_a_wildcard(self):
        text = (DEPLOY / "monitoring.yaml").read_text()
        self.assertNotRegex(text, r"(verbs|resources|apiGroups):\s*\[?\s*[\"']?\*")
        for signal in ("concurrency", "queue", "utilization"):
            self.assertIn(f"pods/{signal}", text)

    def test_the_slots_in_the_utilization_rule_are_the_simulators_slots(self):
        self.assertIn("vllm:num_requests_running / 8", (DEPLOY / "monitoring.yaml").read_text())
        self.assertIn("max-num-seqs: 8", (DEPLOY / "servers.yaml").read_text())

    def test_the_cluster_workflows_pin_their_runner(self):
        for name in ("cluster.yml", "cluster-run.yml"):
            text = (ROOT / ".github/workflows" / name).read_text()
            runners = re.findall(r"^\s+runs-on:\s*(\S+)", text, re.M)
            with self.subTest(workflow=name):
                self.assertTrue(runners)
                self.assertEqual(set(runners), {"ubuntu-24.04"})

    def test_every_signal_has_an_autoscaler_and_a_recorded_series(self):
        monitoring = (DEPLOY / "monitoring.yaml").read_text()
        for signal in ("concurrency", "queue", "utilization"):
            with self.subTest(signal=signal):
                self.assertTrue((DEPLOY / "hpa" / f"{signal}.yaml").exists())
                self.assertIn(f"record: iab_{signal}", monitoring)

    def test_the_autoscaler_targets_are_the_simulations_defaults(self):
        from inference_autoscaling_bench.policies import SIGNALS
        expected = {"concurrency": "6", "queue": "1", "utilization": "600m"}
        for signal, (_, target) in SIGNALS.items():
            if signal in expected:
                text = (DEPLOY / "hpa" / f"{signal}.yaml").read_text()
                value = re.search(r'averageValue: "?([\w.]+)"?', text).group(1)
                with self.subTest(signal=signal):
                    self.assertEqual(value, expected[signal])
                    self.assertEqual(float(target), 0.6 if signal == "utilization" else float(expected[signal]))


class KedaTests(unittest.TestCase):
    """KEDA must scale on exactly what the HPA scales on, so a difference between them is the path, not the policy."""

    def test_every_signal_has_a_scaled_object_beside_its_hpa(self):
        self.assertEqual(sorted(p.name for p in (DEPLOY / "keda").glob("*.yaml")),
                         sorted(p.name for p in (DEPLOY / "hpa").glob("*.yaml")))

    def test_keda_sums_the_series_prometheus_records_for_its_signal(self):
        recorded = set(re.findall(r"record: iab_(\w+)", (DEPLOY / "monitoring.yaml").read_text()))
        for path in (DEPLOY / "keda").glob("*.yaml"):
            query = re.search(r"query: (.+)", path.read_text()).group(1)
            with self.subTest(file=path.name):
                self.assertEqual(query, f'sum(iab_{path.stem}{{namespace="iab"}})')
                self.assertIn(path.stem, recorded)

    def test_keda_targets_the_hpas_value_as_an_average_per_pod(self):
        for path in (DEPLOY / "keda").glob("*.yaml"):
            text = path.read_text()
            hpa = re.search(r'averageValue: "?([\w.]+)"?', (DEPLOY / "hpa" / path.name).read_text()).group(1)
            hpa_value = float(hpa[:-1]) / 1000 if hpa.endswith("m") else float(hpa)
            with self.subTest(file=path.name):
                self.assertIn("metricType: AverageValue", text)
                self.assertEqual(float(re.search(r'threshold: "([\d.]+)"', text).group(1)), hpa_value)

    def test_keda_has_the_hpas_bounds_and_scale_down_window(self):
        for path in (DEPLOY / "keda").glob("*.yaml"):
            text = path.read_text()
            with self.subTest(file=path.name):
                for setting in ("minReplicaCount: ${MIN_REPLICAS}", "maxReplicaCount: ${MAX_REPLICAS}",
                                "scaleDown: {stabilizationWindowSeconds: ${DOWN_WINDOW_S}}", "scaleTargetRef: {name: sim}"):
                    self.assertIn(setting, text)

    def test_keda_is_installed_from_the_pinned_manifest_with_the_pinned_images(self):
        text = (SCRIPTS / "deploy-keda.sh").read_text()
        self.assertIn('sha256sum -c -', text)
        self.assertIn("${KEDA_MANIFEST_SHA256}", text)
        self.assertIn("releases/download/${KEDA_VERSION}/keda-${tag}.yaml", text)
        for key in ("KEDA_IMAGE", "KEDA_METRICS_APISERVER_IMAGE", "KEDA_ADMISSION_WEBHOOKS_IMAGE"):
            with self.subTest(image=key):
                self.assertIn("${%s}" % key, text)
        self.assertIn("--server-side", text)   # the CRDs are too large for a client-side apply

    def test_the_image_swap_replaces_each_image_exactly_once(self):
        # The swap refuses a manifest that does not name an image exactly once, so a new KEDA release that renames or
        # duplicates one fails the install instead of running an unpinned image.
        text = (SCRIPTS / "deploy-keda.sh").read_text()
        self.assertIn('grep -c "image: ghcr.io/kedacore/${name}:${tag}$" "$manifest")" = 1', text)
        names = re.findall(r'"(keda[a-z-]*):\$\{(KEDA_[A-Z_]+)\}"', text)
        self.assertEqual(sorted(n for n, _ in names), ["keda", "keda-admission-webhooks", "keda-metrics-apiserver"])
        for name, key in names:
            self.assertIn(f"/{name}:", versions()[key])

    def test_redeploying_the_servers_removes_either_autoscaler_first(self):
        text = (SCRIPTS / "deploy-servers.sh").read_text()
        servers = text.index("delete deployment sim")
        for autoscaler in ("delete scaledobject sim", "delete hpa sim"):
            with self.subTest(autoscaler=autoscaler):
                self.assertLess(text.index(autoscaler), servers)

    def test_a_keda_run_waits_for_the_autoscaler_keda_creates_to_read_the_external_metric(self):
        run = (SCRIPTS / "run.sh").read_text()
        self.assertIn('keda-*)', run)
        self.assertLess(run.index("scripts/deploy-monitoring.sh"), run.index("scripts/deploy-keda.sh"))   # KEDA asks Prometheus
        self.assertLess(run.index("scripts/deploy-keda.sh"), run.index('scripts/apply-keda.sh "$signal"'))
        self.assertIn("hpa=keda-hpa-sim value='{.status.currentMetrics[0].external.current.averageValue}'", run)
        self.assertIn("kubectl -n \"$NS\" get hpa keda-hpa-sim", (SCRIPTS / "apply-keda.sh").read_text())

    def test_the_cluster_workflow_smoke_tests_keda_on_its_own_cluster(self):
        text = (ROOT / ".github/workflows/cluster.yml").read_text()
        jobs = re.split(r"^  (?=[a-z-]+:\n)", text.split("\njobs:\n", 1)[1], flags=re.M)
        keda = next(j for j in jobs if j.startswith("keda-smoke:"))
        self.assertIn("scripts/smoke-keda.sh", keda)
        self.assertNotIn("scripts/smoke.sh", keda)   # the HPA's smoke test applies an HPA to the same Deployment
        self.assertIn("scripts/cluster-up.sh", keda)

    def test_the_run_workflow_offers_every_policy_the_run_script_takes(self):
        text = (ROOT / ".github/workflows/cluster-run.yml").read_text()
        for policy in ("static-N", "hpa-SIGNAL", "keda-SIGNAL"):
            self.assertIn(policy, text)
        for signal in ("concurrency", "queue", "utilization"):
            self.assertTrue((DEPLOY / "hpa" / f"{signal}.yaml").exists() and (DEPLOY / "keda" / f"{signal}.yaml").exists())
            self.assertIn(signal, text)

    def test_keda_asks_the_same_prometheus(self):
        for path in (DEPLOY / "keda").glob("*.yaml"):
            self.assertIn("serverAddress: http://prometheus.monitoring.svc:9090", path.read_text())


if __name__ == "__main__":
    unittest.main()
