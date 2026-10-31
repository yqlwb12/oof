"""Brainfuck: parse it, tidy it, run it.

The interesting part is not the interpreter -- eight instructions, a tape of
bytes, that is an afternoon -- but the compiler in front of it, which turns
``+++++`` into one addition and ``[->+<]`` into a single multiply-move.  The
tests run every program twice, optimised and not, and insist the output is
identical.
"""

from __future__ import annotations

__all__ = ["BrainfuckError", "OPS", "compile_source", "optimize_ops", "parse", "run"]

#: Everything Brainfuck considers an instruction.
OPS = "+-<>[].,"


class BrainfuckError(Exception):
    """A malformed program, or a program that ran off the tape."""

    def __init__(self, message: str, position: int | None = None):
        self.position = position
        if position is not None:
            message = "%s (at instruction %d)" % (message, position)
        super().__init__(message)


def _tok(code: str, arg: int = 0) -> list:
    """Instructions are ``[code, argument]`` pairs; lists so compilation can
    splice them in place."""
    return [code, arg]


def parse(source: str) -> list:
    """Strip comments and merge runs of the same instruction."""
    ops = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char in OPS:
            if char in "+-<>":
                total = 0
                while index < length and source[index] == char:
                    total += 1
                    index += 1
                ops.append(_tok(char, total))
                continue
            ops.append(_tok(char))
        index += 1
    return ops


def _match_brackets(ops: list) -> dict:
    """Pair up ``[`` and ``]``, complaining about the first stray bracket."""
    stack = []
    pairs = {}
    for position, (code, _) in enumerate(ops):
        if code == "[":
            stack.append(position)
        elif code == "]":
            if not stack:
                raise BrainfuckError("unmatched ']'", position)
            opening = stack.pop()
            pairs[opening] = position
            pairs[position] = opening
    if stack:
        raise BrainfuckError("unmatched '['", stack[-1])
    return pairs


def _body(ops: list, start: int, end: int) -> list:
    """Instructions strictly inside a loop that opens at *start*."""
    return ops[start + 1:end]


def _loop_is_multiplicative(body: list) -> bool:
    """True when a loop's body only walks and adds, and comes back home."""
    if not body:
        return False
    guard = body[0]
    if guard[0] not in "+-" or guard[1] != 1:
        return False
    offset = 0
    for code, arg in body:
        if code in "><":
            offset += arg if code == ">" else -arg
        elif code not in "+-":
            return False
    return offset == 0


def _factors(body: list) -> tuple:
    """Collapse ``[->+<]``-style bodies into (offset, delta) pairs.

    A ``+`` guard runs the body ``256 - value`` times rather than ``value``
    times, which is the same as stepping by ``-delta`` -- so the sign flips.
    Getting this wrong is invisible until someone writes ``[+>+<]``.
    """
    offset = 0
    tally = {}
    for code, arg in body[1:]:
        if code == ">":
            offset += arg
        elif code == "<":
            offset -= arg
        elif code == "+":
            tally[offset] = tally.get(offset, 0) + arg
        elif code == "-":
            tally[offset] = tally.get(offset, 0) - arg

    sign = -1 if body[0][0] == "+" else 1
    factors = []
    for offset, delta in tally.items():
        delta = (delta * sign) % 256
        if delta:
            factors.append((offset, delta))
    return tuple(sorted(factors))


def optimize_ops(ops: list) -> list:
    """Peephole pass: clear loops, multiply loops, then resolve jumps."""
    out = []
    index = 0
    length = len(ops)
    pairs = _match_brackets(ops)

    while index < length:
        code, arg = ops[index]

        # [-] or [+] : assign zero, however many cells away we started.
        if code == "[":
            close = pairs[index]
            body = _body(ops, index, close)
            if len(body) == 1 and body[0][0] in "+-" and body[0][1] % 256 == 1:
                out.append(_tok("Z"))
                index = close + 1
                continue

            # [->+<] and friends: one multiply-move instead of a loop.
            if _loop_is_multiplicative(body):
                factors = _factors(body)
                if factors:
                    out.append(_tok("M", factors))
                    index = close + 1
                    continue

        out.append(_tok(code, arg))
        index += 1

    jumps = _match_brackets(out)
    for position, (code, _) in enumerate(out):
        if code in "[]":
            out[position][1] = jumps[position]
    return out


def compile_source(source: str, *, optimize: bool = True) -> list:
    """Parse, optionally tidy, and resolve jumps."""
    ops = parse(source)
    _match_brackets(ops)  # fail early, with a source-relative position
    return optimize_ops(ops) if optimize else _resolve(ops)


def _resolve(ops: list) -> list:
    jumps = _match_brackets(ops)
    resolved = []
    for position, (code, arg) in enumerate(ops):
        resolved.append([code, jumps[position] if code in "[]" else arg])
    return resolved


def run(
    source: str,
    stdin: str = "",
    *,
    cells: int = 30000,
    wrap: bool = True,
    optimize: bool = True,
) -> str:
    """Execute *source* and return everything it printed."""
    if cells < 1:
        raise ValueError("cells must be at least 1")
    program = compile_source(source, optimize=optimize)
    tape = bytearray(cells)
    pointer = 0
    output = []
    feed = iter(stdin)
    pc = 0
    length = len(program)

    while pc < length:
        code, arg = program[pc]

        if code == "+":
            tape[pointer] = (tape[pointer] + arg) & 0xFF
        elif code == "-":
            tape[pointer] = (tape[pointer] - arg) & 0xFF
        elif code == ">":
            pointer += arg
            if pointer >= cells:
                if not wrap:
                    raise BrainfuckError("ran off the right end of the tape", pc)
                pointer %= cells
        elif code == "<":
            pointer -= arg
            if pointer < 0:
                if not wrap:
                    raise BrainfuckError("ran off the left end of the tape", pc)
                pointer %= cells
        elif code == ".":
            output.append(chr(tape[pointer]))
        elif code == ",":
            char = next(feed, None)
            tape[pointer] = ord(char) & 0xFF if char is not None else 0
        elif code == "Z":
            tape[pointer] = 0
        elif code == "M":
            value = tape[pointer]
            if value:
                for offset, delta in arg:
                    index = pointer + offset
                    if index < 0 or index >= cells:
                        if not wrap:
                            raise BrainfuckError("multiply wrote off the tape", pc)
                        index %= cells
                    tape[index] = (tape[index] + delta * value) & 0xFF
            tape[pointer] = 0
        elif code == "[":
            if tape[pointer] == 0:
                pc = arg
        elif code == "]":
            if tape[pointer] != 0:
                pc = arg

        pc += 1

    return "".join(output)
