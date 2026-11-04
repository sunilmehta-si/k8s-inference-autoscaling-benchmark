import unittest

from inference_autoscaling_bench import client
from inference_autoscaling_bench.workload import Request
from tests.fakes import FakeModelServer


def trace(*rows):
    return [Request(i, *row) for i, row in enumerate(rows)]


class BodyTests(unittest.TestCase):
    def test_the_request_pins_both_ends_of_the_response_length(self):
        import json
        payload = json.loads(client.body(Request(0, 1.0, 5, 40), "m"))
        self.assertEqual((payload["max_tokens"], payload["min_tokens"]), (40, 40))
        self.assertTrue(payload["stream"] and payload["stream_options"]["include_usage"])
        self.assertEqual(payload["messages"][0]["content"].split(), ["a"] * 5)

    def test_the_prompt_has_the_requested_number_of_words(self):
        self.assertEqual(len(client.prompt_for(600).split()), 600)


class RunTests(unittest.TestCase):
    def test_a_stream_is_timed_to_its_first_chunk(self):
        with FakeModelServer(first_token_s=0.2, chunk_s=0.0) as server:
            [result] = client.run(server.url, "m", trace((0.0, 7, 3)), lead_s=0.0)
        self.assertTrue(result.ok)
        self.assertGreaterEqual(result.ttft_s, 0.2)
        self.assertLess(result.ttft_s, 1.0)
        self.assertGreaterEqual(result.e2e_s, result.ttft_s)
        self.assertEqual((result.output_chunks, result.prompt_tokens, result.completion_tokens), (3, 7, 3))
        self.assertEqual((result.requested_prompt_tokens, result.requested_output_tokens), (7, 3))

    def test_requests_are_sent_at_their_arrival_times_and_in_trace_order(self):
        with FakeModelServer() as server:
            results = client.run(server.url, "m", trace((0.0, 5, 1), (0.3, 5, 1), (0.6, 5, 1)), lead_s=0.0)
        self.assertEqual([r.index for r in results], [0, 1, 2])
        self.assertEqual([r.scheduled_s for r in results], [0.0, 0.3, 0.6])
        for r in results:
            self.assertLess(r.lateness_s, 0.15)

    def test_a_slow_answer_does_not_delay_the_next_request(self):
        # Open loop: the second request is sent on schedule while the first is still waiting for its first token.
        with FakeModelServer(first_token_s=0.6) as server:
            results = client.run(server.url, "m", trace((0.0, 5, 1), (0.1, 5, 1)), lead_s=0.0)
        self.assertLess(results[1].lateness_s, 0.15)
        self.assertGreaterEqual(results[1].ttft_s, 0.6)

    def test_an_error_status_is_a_failure_with_its_reason(self):
        with FakeModelServer(status=503) as server:
            [result] = client.run(server.url, "m", trace((0.0, 5, 1)), lead_s=0.0)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 503)
        self.assertIn("overloaded", result.error)
        self.assertIsNone(result.ttft_s)

    def test_a_server_that_is_not_there_is_a_failure_not_a_crash(self):
        [result] = client.run("http://127.0.0.1:9", "m", trace((0.0, 5, 1)), timeout=2, lead_s=0.0)
        self.assertFalse(result.ok)
        self.assertEqual(result.status, 0)
        self.assertTrue(result.error)

    def test_a_burst_of_forty_requests_all_arrive(self):
        with FakeModelServer(first_token_s=0.05) as server:
            results = client.run(server.url, "m", trace(*[(0.0, 5, 1)] * 40), lead_s=0.0)
            self.assertEqual(len(server.requests), 40)
        self.assertTrue(all(r.ok for r in results))

    def test_a_non_http_endpoint_is_refused(self):
        with self.assertRaises(ValueError):
            client.run("https://example.com", "m", trace((0.0, 5, 1)))


if __name__ == "__main__":
    unittest.main()
