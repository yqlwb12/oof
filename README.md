# oof

[![tests](https://github.com/yqlwb12/oof/actions/workflows/ci.yml/badge.svg)](https://github.com/yqlwb12/oof/actions/workflows/ci.yml)

> **Experimental project, for reference and learning only.**
> Published as-is, with no warranty of correctness or fitness for purpose.
> 本项目仅供参考与实验用途，不保证可靠性；生产使用前请自行充分测试。

**Brainfuck, with a peephole pass that earns its keep.** Eight instructions, a tape of bytes, no dependencies.

```console
$ oof examples/hello.bf
Hello World!

$ oof examples/echo.bf -i "echo echo"
echo echo
```

## Why

Writing an interpreter for this language takes about forty lines, which is why
everyone has done it. What nobody bothers with is the compiler in front of it — and
that is the part with the interesting bug in it. So: `oof` merges instruction runs,
turns `[-]` into a single "assign zero" op, recognises `[->+<]`-shaped loops as a
multiply-move, and then proves all of that is safe the only way you can: by running
every test program twice, optimised and raw, and comparing the output byte for byte.

## Install

```console
$ pip install .
$ oof examples/hello.bf
```

Or from the checkout: `PYTHONPATH=src python -m oof examples/hello.bf`.

## Usage

```console
$ oof program.bf                 # run it
$ oof program.bf -i "text"       # feed ',' instructions
$ oof program.bf --dump          # show the compiled program
$ oof program.bf --no-opt        # run the raw instruction stream
$ oof program.bf --nowrap        # error instead of wrapping at the tape ends
$ oof - < program.bf             # read the program from stdin
```

## The compiler

Three passes, in order:

| Source | Compiled | Why |
| --- | --- | --- |
| `+++++` | `+ x5` | one addition instead of five |
| `[-]` / `[+]` | `Z` | assign zero, no loop at all |
| `[->+<]` | `M +1@+1` | multiply-move: `tape[p+1] += tape[p]; tape[p] = 0` |
| `[+>+<]` | `M -1@+1` | a `+` guard runs `256 - v` times, so the step flips sign |

That last row is the one that bites. `[+>+<]` starting from five runs 251 times, not
five, so the multiplier is `-1` and not `+1`. It stays invisible until someone writes
the incrementing guard, which is why the corpus carries two of them.

`M` carries `(offset, delta)` pairs, so `[->>+++<<]` collapses into one instruction
too. Loops whose bodies contain I/O or nested loops are left alone — the pass only
fires when it can prove the shape.

```console
$ oof examples/hello.bf --dump | head -4
   0  +  x8
   1  [  -> 29
   2  >  x1
   3  +  x4
```

Programs that do not terminate are not caught. Nothing in Brainfuck stops you from
writing `+[]`, and no peephole pass will save you.

## Errors

Brackets are matched before anything runs, and the message points at the instruction:

```console
$ printf '+[+' > bad.bf && oof bad.bf
oof: unmatched '[' (at instruction 1)
```

## Tests

```console
$ PYTHONPATH=src python -m unittest discover -s tests -v
```

31 tests. The important one is `test_optimiser_preserves_output`: a corpus of nine
programs (Hello World, an echo, a nested-loop multiplier, a cell that wraps through
255, two incrementing guards) run with `optimize=True` and `optimize=False` on two
different inputs, with the outputs compared. A peephole pass without that test is a
rumour.

## Disclaimer

This repository is a personal experiment, published for reference and learning.
It is not production software.

- **No warranty.** Provided "as is", without warranty of any kind, exactly as the
  licence says. Correctness, fitness for purpose and safety are not guaranteed.
- **Expect changes.** Interfaces, output formats and behaviour may change without
  notice; the test suite describes what the code does today, not a promise about
  tomorrow.
- **Verify before you rely on it.** Read the code, run the tests, and check the
  results yourself in your own environment.

The optimiser is interesting, not certified. It is tested against a corpus, not proven equivalent, and nothing stops a program it is given from looping forever.

本项目仅供学习、参考与实验使用，作者不对其可靠性、准确性与适用性作出任何保证。
在生产环境使用或对外提供服务之前，请自行充分审查代码、评估风险并完成测试。

## Licence

MIT.
