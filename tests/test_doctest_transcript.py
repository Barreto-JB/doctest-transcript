"""CLI contract tests for isolated validation."""

import json
from pathlib import Path
import subprocess
import sys
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "doctest_transcript.py"
LIMIT = 256 * 1024


class TranscriptTests(unittest.TestCase):
    def run_cli(self, data, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args],
            input=data,
            capture_output=True,
            timeout=10,
        )

    def assert_examples(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout), expected)

    def assert_rejected(self, result):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr.splitlines(), [b"error: invalid input"])

    def test_indented_multiline_example_and_utf8_with_crlf(self):
        data = 'Tutorial\r\n\r\n    >>> print(\r\n    ...     "café")\r\n    café'.encode("utf-8")
        self.assert_examples(self.run_cli(data), [
            {"line": 3, "source": 'print(\n    "café")\n', "expected": "café\n"},
        ])

    def test_inclusive_filters_use_example_start_lines(self):
        data = b">>> (\n... 1)\n1\n\n>>> 2\n2\n\n>>> 3\n3\n"
        first = {"line": 1, "source": "(\n1)\n", "expected": "1\n"}
        second = {"line": 5, "source": "2\n", "expected": "2\n"}
        third = {"line": 8, "source": "3\n", "expected": "3\n"}
        for args, expected in (
            (("--start-line", "2", "--end-line", "5"), [second]),
            (("--start-line", "5"), [second, third]),
            (("--end-line", "5"), [first, second]),
            (("--start-line", "9"), []),
        ):
            with self.subTest(args=args):
                self.assert_examples(self.run_cli(data, *args), expected)

    def test_examples_are_never_evaluated(self):
        self.assert_examples(self.run_cli(b">>> raise RuntimeError('example')\n"), [
            {"line": 1, "source": "raise RuntimeError('example')\n", "expected": ""},
        ])

    def test_empty_and_prose_only_inputs(self):
        for data in (b"", b"Just prose\n"):
            with self.subTest(data=data):
                self.assert_examples(self.run_cli(data), [])

    def test_input_limit_is_in_bytes(self):
        data = "é".encode("utf-8") * (LIMIT // 2)
        self.assert_examples(self.run_cli(data), [])
        self.assert_rejected(self.run_cli(data + b"a"))

    def test_invalid_utf8_is_rejected(self):
        self.assert_rejected(self.run_cli(b"\xff"))

    def test_malformed_examples_are_rejected_even_outside_filter(self):
        for malformed in (b">>>no_space\n", b">>> 1  # doctest: +UNKNOWN_OPTION\n"):
            with self.subTest(malformed=malformed):
                data = b">>> 0\n0\n\n" + malformed
                self.assert_rejected(self.run_cli(data, "--end-line", "1"))

    def test_invalid_ranges_and_path_arguments_are_rejected(self):
        for args in (
            ("--start-line", "0"),
            ("--end-line", "-1"),
            ("--end-line", "one"),
            ("--start-line", "2", "--end-line", "1"),
            ("tutorial.txt",),
        ):
            with self.subTest(args=args):
                result = self.run_cli(b"", *args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, b"")
                self.assertTrue(result.stderr)


if __name__ == "__main__":
    unittest.main()
