"""Tests for the oof command line."""

import io
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr

from oof import cli

HELLO = (
    "++++++++[>++++[>++>+++>+++>+<<<<-]>+>+>->>+[<]<-]"
    ">>.>---.+++++++..+++.>>.<-.<.+++.------.--------.>>+.>++."
)


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = cli.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class ProgramFileTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.path = os.path.join(self.directory, "hello.bf")
        with open(self.path, "w", encoding="utf-8") as handle:
            handle.write(HELLO)

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_runs_a_file(self):
        code, out, _ = call(self.path)
        self.assertEqual(code, 0)
        self.assertEqual(out, "Hello World!\n")

    def test_input_is_piped_through(self):
        path = os.path.join(self.directory, "echo.bf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(",[.,]")
        code, out, _ = call(path, "-i", "ping")
        self.assertEqual((code, out), (0, "ping"))

    def test_comment_characters_are_ignored(self):
        # Not one of the eight instructions appears in that sentence.
        path = os.path.join(self.directory, "loud.bf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("note to self add eight then multiply by nine\n++++++++[>+++++++++<-]>.")
        _, out, _ = call(path)
        self.assertEqual(out, "H")

    def test_dump_shows_the_optimised_program(self):
        path = os.path.join(self.directory, "mul.bf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("++++[->+<]")
        code, out, _ = call(path, "--dump")
        self.assertEqual(code, 0)
        self.assertIn("M", out)
        self.assertIn("x4", out)

    def test_dump_without_optimisation_keeps_the_loop(self):
        path = os.path.join(self.directory, "mul.bf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("[->+<]")
        _, out, _ = call(path, "--dump", "--no-opt")
        self.assertIn("[", out)
        self.assertNotIn("M", out)


class FailureTest(unittest.TestCase):
    def test_missing_file(self):
        code, _, err = call("definitely-not-here.bf")
        self.assertEqual(code, 1)
        self.assertIn("cannot read", err)

    def test_broken_program(self):
        directory = tempfile.mkdtemp()
        path = os.path.join(directory, "bad.bf")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("+[+")
        try:
            code, _, err = call(path)
            self.assertEqual(code, 1)
            self.assertIn("unmatched", err)
        finally:
            os.remove(path)
            os.rmdir(directory)

    def test_version(self):
        with self.assertRaises(SystemExit) as caught:
            call("--version")
        self.assertEqual(caught.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
