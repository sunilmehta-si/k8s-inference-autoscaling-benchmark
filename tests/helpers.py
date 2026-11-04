from inference_autoscaling_bench import workload
from inference_autoscaling_bench.policies import Policy
from inference_autoscaling_bench.workload import Request


def tiny_workload(duration=60, slo=2.0):
    return workload.from_dict({
        "name": "tiny", "description": "d", "duration_s": duration, "schedule": [[0, 1], [duration, 1]],
        "prompt_tokens": {"median": 100, "sigma": 0.5, "max": 1000},
        "output_tokens": {"median": 50, "sigma": 0.5, "max": 500}, "slo_ttft_s": slo,
    })


def trace(*rows):
    """Requests from (arrival, prompt tokens, output tokens) rows."""
    return [Request(i, *row) for i, row in enumerate(rows)]


class Scripted(Policy):
    """Starts with `initial` pods and asks for the replica count `script` gives at each sync second."""
    name = "scripted"

    def __init__(self, initial, script):
        self._initial, self.script = initial, script

    def initial(self, bounds):
        return self._initial

    def decide(self, obs, bounds):
        return self.script.get(obs.now)
