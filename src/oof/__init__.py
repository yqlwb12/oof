"""oof -- Brainfuck with a compiler that pulls its weight.

    >>> from oof import run
    >>> run("++++++++[>+++++++++<-]>.")
    'H'

Eight instructions, a tape of bytes, and a peephole pass that turns
``[->+<]`` into one multiply-move.
"""

from .core import BrainfuckError, OPS, compile_source, optimize_ops, parse, run

__version__ = "0.1.1"

__all__ = [
    "BrainfuckError",
    "OPS",
    "__version__",
    "compile_source",
    "optimize_ops",
    "parse",
    "run",
]
