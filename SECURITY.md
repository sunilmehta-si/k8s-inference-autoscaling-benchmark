# Security policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[security advisory form](https://github.com/sunilmehta-si/k8s-inference-autoscaling-benchmark/security/advisories/new)
rather than in a public issue. You will get an answer within a week.

## What this project runs

- The package has no dependencies and makes no network calls. It reads a workload file and writes result files.
- Workflows start with a read-only token, pin third-party actions to commit SHAs, and run bash with pipefail.
- Dependabot proposes updates only after a release is 14 days old; security updates are not delayed.
- Every pull request is reviewed by [agentic-code-review-tool](https://github.com/sunilmehta-si/agentic-code-review-tool).
