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
        for key in ("KIND_NODE_IMAGE", "SIM_IMAGE", "PROMETHEUS_IMAGE", "PROMETHEUS_ADAPTER_IMAGE"):
            with self.subTest(image=key):
                self.assertRegex(v[key], r"@sha256:[0-9a-f]{64}$")

    def test_the_image_tags_agree_with_the_versions_beside_them(self):
        v = versions()
        self.assertIn(f":{v['PROMETHEUS_VERSION']}@", v["PROMETHEUS_IMAGE"])
        self.assertIn(f":{v['PROMETHEUS_ADAPTER_VERSION']}@", v["PROMETHEUS_ADAPTER_IMAGE"])

    def test_the_downloaded_binary_has_a_checksum(self):
        self.assertRegex(versions()["KIND_SHA256_LINUX_AMD64"], r"^[0-9a-f]{64}$")

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
        hpa = set()
        for path in (DEPLOY / "hpa").glob("*.yaml"):
            hpa |= set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", path.read_text()))
        listed = set(re.findall(r"\$\{([A-Z_]+)\}", re.search(r"envsubst '([^']*)'", (SCRIPTS / "apply-hpa.sh").read_text()).group(1)))
        self.assertEqual(hpa, listed)

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

    def test_the_slots_in_the_utilization_rule_are_the_simulators_slots(self):
        self.assertIn("vllm:num_requests_running / 8", (DEPLOY / "monitoring.yaml").read_text())
        self.assertIn("max-num-seqs: 8", (DEPLOY / "servers.yaml").read_text())

    def test_the_cluster_workflow_pins_its_actions_and_runner(self):
        text = (ROOT / ".github/workflows/cluster.yml").read_text()
        runners = re.findall(r"^\s+runs-on:\s*(\S+)", text, re.M)
        self.assertTrue(runners)
        self.assertEqual(set(runners), {"ubuntu-24.04"})


if __name__ == "__main__":
    unittest.main()
