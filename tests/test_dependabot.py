import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MIN_RELEASE_AGE_DAYS = 14


class DependabotTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT / ".github/dependabot.yml").read_text()
        self.blocks = re.split(r"^  - package-ecosystem: ", self.text, flags=re.M)[1:]

    def test_actions_and_pip_are_both_kept_current(self):
        self.assertEqual(sorted(b.split()[0] for b in self.blocks), ["github-actions", "pip"])

    def test_every_update_waits_the_minimum_release_age(self):
        for block in self.blocks:
            with self.subTest(ecosystem=block.split()[0]):
                days = re.search(r"default-days:\s*(\d+)", block)
                self.assertIsNotNone(days)
                self.assertGreaterEqual(int(days.group(1)), MIN_RELEASE_AGE_DAYS)

    def test_every_workflow_action_is_pinned_to_a_commit(self):
        for path in (ROOT / ".github/workflows").glob("*.yml"):
            for line in path.read_text().splitlines():
                match = re.search(r"uses:\s*([^\s@]+)@(\S+)", line)
                if match and not match.group(1).startswith("./"):
                    with self.subTest(workflow=path.name, action=match.group(1)):
                        self.assertRegex(match.group(2), r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
