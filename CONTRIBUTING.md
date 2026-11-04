# Contributing

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install -e .
make test        # the unit tests; Python 3.10 or later
make results     # regenerate every committed dataset; git diff shows any change
```

- **A result changes only when the model does.** The datasets in `results/` are what `make results` gives. CI
  regenerates them and fails on any difference, and a test re-runs the first seed of every policy from its spec. If
  you change the simulator, a policy, a workload or a spec, run `make results` and commit the new numbers with the
  change that caused them, with the README's numbers updated: a test holds each one to the saved results.
- **A claim needs a test.** Anything the README says about a result is checked against `results/`. A new claim gets a
  check in `tests/test_committed_results.py`.
- **Say what was chosen before the results.** A new policy target, objective or workload is decided before runs are
  compared, and the methodology says so. If a setting changes after a first look, say that too.
- **No dependencies.** The package uses the standard library only; the tests do too.
- **Pins.** Third-party actions are pinned to a commit SHA that was checked against the release tag. Dependabot waits
  14 days after a release before proposing an update, and a hand-made bump should too.
- Pull requests are reviewed by agentic-code-review-tool on their changed lines; a high finding blocks.
