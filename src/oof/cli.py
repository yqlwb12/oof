"""Command line front end for oof."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .core import BrainfuckError, compile_source, run

__version__ = "0.1.0"


def _signed(delta: int) -> int:
    """Deltas are stored mod 256; print them the way a human reads them."""
    return delta - 256 if delta > 127 else delta


def _describe(program: list) -> str:
    lines = []
    for index, (code, arg) in enumerate(program):
        if code == "M":
            factors = " ".join(
                "%+d@%+d" % (_signed(delta), offset) for offset, delta in arg
            )
            lines.append("%4d  M  %s" % (index, factors))
        elif code in "[]":
            lines.append("%4d  %s  -> %d" % (index, code, arg))
        elif code in "+-<>":
            lines.append("%4d  %s  x%d" % (index, code, arg))
        else:
            lines.append("%4d  %s" % (index, code))
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oof",
        description="Run a Brainfuck program, with a compiler that pulls its weight.",
        epilog=(
            "examples:\n"
            "  oof hello.bf\n"
            "  oof echo.bf -i 'hello'\n"
            "  oof hello.bf --dump      # see what the optimiser produced\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", metavar="FILE", help="program to run, or - for stdin")
    parser.add_argument("-i", "--input", default="", metavar="TEXT",
                        help="characters to feed to ',' instructions")
    parser.add_argument("--cells", type=int, default=30000, metavar="N",
                        help="tape size (default: 30000)")
    parser.add_argument("--nowrap", action="store_true",
                        help="error instead of wrapping the pointer at the ends")
    parser.add_argument("--no-opt", dest="optimize", action="store_false",
                        help="run the raw instruction stream")
    parser.add_argument("--dump", action="store_true",
                        help="print the compiled program instead of running it")
    parser.add_argument("--version", action="version", version="oof " + __version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.file == "-":
            source = sys.stdin.read()
        else:
            source = Path(args.file).read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        sys.stderr.write("oof: cannot read %s: %s\n" % (args.file, exc.strerror or exc))
        return 1

    if args.dump:
        try:
            program = compile_source(source, optimize=args.optimize)
        except BrainfuckError as exc:
            sys.stderr.write("oof: %s\n" % exc)
            return 1
        sys.stdout.write(_describe(program) + "\n")
        return 0

    try:
        output = run(
            source,
            args.input,
            cells=args.cells,
            wrap=not args.nowrap,
            optimize=args.optimize,
        )
    except BrainfuckError as exc:
        sys.stderr.write("oof: %s\n" % exc)
        return 1

    sys.stdout.write(output)
    sys.stdout.flush()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
