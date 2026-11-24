"""Extract Python doctest transcripts from standard input as JSON."""

import argparse
import doctest
import json
import sys


MAX_INPUT_BYTES = 256 * 1024


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument(
        "--start-line", type=int, default=1,
        help="first example start line to include (default: 1)",
    )
    parser.add_argument(
        "--end-line", type=int,
        help="last example start line to include (inclusive)",
    )
    args = parser.parse_args(argv)
    if args.start_line < 1 or (
        args.end_line is not None and args.end_line < args.start_line
    ):
        parser.error("line bounds must be positive and in ascending order")

    try:
        data = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(data) > MAX_INPUT_BYTES:
            raise ValueError
        tutorial = data.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
        examples = doctest.DocTestParser().get_examples(tutorial)
    except (OSError, ValueError):
        print("error: invalid input", file=sys.stderr)
        return 2

    transcript = []
    for example in examples:
        line = example.lineno + 1
        if line >= args.start_line and (args.end_line is None or line <= args.end_line):
            transcript.append({
                "line": line,
                "source": example.source,
                "expected": example.want,
            })
    print(json.dumps(transcript))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
