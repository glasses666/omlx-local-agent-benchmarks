import unittest

from omlx_benchmark.evaluators import python_function_score


class CodeScoringTests(unittest.TestCase):
    def test_python_function_score_tolerates_leading_explanation(self) -> None:
        text = """Here's the updated function:\n\ndef sum_even(nums):\n    return sum(x for x in nums if x % 2 == 0)\n"""
        score, details = python_function_score(
            text,
            "sum_even",
            [{"args": [[1, 2, 3, 4]], "expected": 6}],
        )
        self.assertEqual(score, 100.0)
        self.assertIn("results", details)

    def test_python_function_score_returns_zero_for_invalid_code(self) -> None:
        score, details = python_function_score(
            "not valid python(",
            "sum_even",
            [{"args": [[1, 2]], "expected": 2}],
        )
        self.assertEqual(score, 0.0)
        self.assertIn("error", details)

    def test_python_function_score_allows_round_builtin(self) -> None:
        score, details = python_function_score(
            "def apply_discount(total, percent):\n    return max(0, round(total * (1 - percent / 100), 2))\n",
            "apply_discount",
            [
                {"args": [100, 25], "expected": 75.0},
                {"args": [10, 200], "expected": 0.0},
            ],
        )
        self.assertEqual(score, 100.0)
        self.assertIn("results", details)
