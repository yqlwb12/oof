"""Tests for the compiler and the interpreter.

The centrepiece is ``test_optimiser_preserves_output``: every program in the
corpus is executed twice, once compiled and once raw, and the outputs must
match.  That is the only way to trust a peephole pass.
"""

import unittest

from oof.core import BrainfuckError, compile_source, optimize_ops, parse, run

HELLO = (
    "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]"
    ">>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."
)

CORPUS = [
    HELLO,
    "++++++++[>+++++++++<-]>+.",          # 'H' by multiplication
    ",[.,]",                             # echo until end of input
    "-[->+<]>.",                         # counts 255 down to zero
    "+++++[>++++<-]>[->>+<<]>>.",        # multiply twice, nested moves
    "++[>++[>++<-]<-]>>.",               # nested loops
    "+[>+<-]>.",                         # one multiply, one print
]


class ParseTest(unittest.TestCase):
    def test_comments_are_dropped(self):
        self.assertEqual(parse("a+b c[d]"), [["+", 1], ["[", 0], ["]", 0]])

    def test_runs_are_merged(self):
        self.assertEqual(parse("+++++"), [["+", 5]])
        self.assertEqual(parse(">>>"), [[">", 3]])

    def test_opposite_instructions_stay_apart(self):
        self.assertEqual(parse("><"), [[">", 1], ["<", 1]])


class OptimiserTest(unittest.TestCase):
    def test_clear_loop_becomes_one_op(self):
        self.assertEqual([code for code, _ in compile_source("[-]")], ["Z"])

    def test_move_loop_becomes_a_multiply(self):
        program = compile_source("[->+<]")
        self.assertEqual(len(program), 1)
        self.assertEqual(program[0][0], "M")
        self.assertEqual(program[0][1], ((1, 1),))

    def test_plain_loops_are_left_alone(self):
        codes = [code for code, _ in compile_source("+[>+<]")]
        self.assertIn("[", codes)
        self.assertIn("]", codes)

    def test_dump_is_stable(self):
        once = compile_source(HELLO)
        twice = compile_source(HELLO)
        self.assertEqual(once, twice)

    def test_jump_targets_point_at_brackets(self):
        program = compile_source("+[>+<]")
        for index, (code, arg) in enumerate(program):
            if code in "[]":
                self.assertIn(program[arg][0], "[]")
                self.assertNotEqual(arg, index)

    def test_optimiser_shrinks_the_program(self):
        source = "++++[->+<]+++++[-]"
        self.assertLess(len(optimize_ops(parse(source))), len(parse(source)))


class RunTest(unittest.TestCase):
    def test_hello_world(self):
        self.assertEqual(run(HELLO), "Hello World!\n")

    def test_hello_world_without_optimisation(self):
        self.assertEqual(run(HELLO, optimize=False), "Hello World!\n")

    def test_echo(self):
        self.assertEqual(run(",[.,]", "abc"), "abc")

    def test_missing_input_reads_zero(self):
        self.assertEqual(run(",."), "\x00")

    def test_clear_loop(self):
        self.assertEqual(run("+++++[-]."), "\x00")

    def test_wraps_at_256(self):
        self.assertEqual(run("-."), chr(255))
        self.assertEqual(run("+" * 256 + "."), "\x00")

    def test_tape_wraps_by_default(self):
        # Two cells: stepping right from the last one lands back on the first.
        self.assertEqual(run("+>+>.", cells=2), "\x01")
        self.assertEqual(run("<+.", cells=2), "\x01")

    def test_nowrap_reports_the_fault(self):
        with self.assertRaises(BrainfuckError):
            run(">", cells=1, wrap=False)

    def test_unmatched_brackets(self):
        for source in ("[", "]", "[[", "]["):
            with self.assertRaises(BrainfuckError):
                run(source)

    def test_bad_tape_size(self):
        with self.assertRaises(ValueError):
            run("+", cells=0)


class DifferentialTest(unittest.TestCase):
    def test_optimiser_preserves_output(self):
        for program in CORPUS:
            for stdin in ("", "abc"):
                self.assertEqual(
                    run(program, stdin, optimize=True),
                    run(program, stdin, optimize=False),
                    msg="program %r with input %r" % (program, stdin),
                )


if __name__ == "__main__":
    unittest.main()
