import unittest

from omlx_benchmark.scoring import redistribute_vision_weight


class ScoringTests(unittest.TestCase):
    def test_redistribute_vision_weight_for_non_vision_models(self) -> None:
        weights = {
            "speed": 10,
            "chat": 20,
            "instruction": 10,
            "code": 20,
            "tool": 15,
            "long_context": 15,
            "vision": 10,
        }

        redistributed = redistribute_vision_weight(weights)

        self.assertNotIn("vision", redistributed)
        self.assertAlmostEqual(sum(redistributed.values()), 100.0)
        self.assertGreater(redistributed["chat"], 20.0)
