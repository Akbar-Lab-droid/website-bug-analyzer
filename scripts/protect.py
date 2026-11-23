#!/usr/bin/env python3
"""Build a protected copy of a Python program.

Usage:
    python3 scripts/protect.py analyzer.py
    python3 scripts/protect.py analyzer.py --out dist
    python3 scripts/protect.py analyzer.py --smoke "--help"

What it does
------------
Compiles the program to optimised bytecode (.pyc) with docstrings
stripped (optimisation level 2). The result still runs exactly like
the original:

    python3 dist/analyzer.pyc https://example.com

but it is hard to read: no source text, no comments, no docstrings,
no readable names. That stops casual copying -- someone who only gets
the .pyc cannot just open it and rewrite it.

What it does NOT do (read this before relying on it)
-----------------------------------------------------
Bytecode can be decompiled back to readable source with public tools,
so this is a speed bump, not a vault. It stops casual recoding, not a
determined person. Real protection needs one of these instead:

  * ship a compiled binary (PyInstaller, Nuitka, Cython),
  * keep the repository private,
  * change the licence from MIT (which allows reuse) to a licence
    that forbids it.

This tool also deliberately never hides code inside an encoded blob.
Encoded payloads look exactly like malware to every scanner --
including repo-safety-check, which flags them -- so the protected
build is plain bytecode, nothing more.

The .pyc file is a build artifact: it is ignored by .gitignore and
never committed. The readable source stays in the repository, and the
protected copy is built on demand whenever you share the program.
"""

import argparse
import py_compile
import re
import shlex
import subprocess
import sys
from pathlib import Path

# Response times in program output, e.g. "687 ms". Two runs never print
# the same number, so the comparison ignores them.
_TIMING = re.compile(r"\d+ ms")


def build(source: Path, out_dir: Path) -> Path:
    """Compile source to optimised bytecode and return the .pyc path."""
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / (source.stem + ".pyc")
    py_compile.compile(str(source), cfile=str(target), doraise=True, optimize=2)
    return target


def run_python(program: Path, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a .py or .pyc file and capture the result."""
    return subprocess.run(
        [sys.executable, str(program)] + args,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _normalise(text: str, target_name: str, source_name: str) -> str:
    """Make two runs comparable: same file name, same whitespace.

    The file name differs (analyzer.py vs analyzer.pyc), which also
    shifts argparse's usage-line wrapping by one space. Collapsing
    whitespace removes that formatting noise while keeping every word
    and number. Response times are normalised too, since they vary
    between any two runs of a network tool.
    """
    text = text.replace(target_name, source_name)
    text = _TIMING.sub("N ms", text)
    return " ".join(text.split())


def verify(source: Path, target: Path, smoke_args: list[str], cwd: Path) -> bool:
    """Check the protected copy behaves exactly like the original."""
    original = run_python(source, smoke_args, cwd)
    protected = run_python(target, smoke_args, cwd)
    same = (
        original.returncode == protected.returncode
        and _normalise(original.stdout, target.name, source.name)
        == _normalise(protected.stdout, target.name, source.name)
    )
    if not same:
        print("Verification FAILED: protected copy behaves differently.")
        print(f"  original:  exit {original.returncode}, "
              f"{len(original.stdout)} bytes of output")
        print(f"  protected: exit {protected.returncode}, "
              f"{len(protected.stdout)} bytes of output")
    return same


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build a protected (bytecode) copy of a Python program."
    )
    parser.add_argument("source", help="Python file to protect, e.g. analyzer.py")
    parser.add_argument("--out", default="dist",
                        help="Output directory for the .pyc file (default: dist)")
    parser.add_argument("--smoke", default="https://example.com",
                        help="Arguments for the smoke test run on both copies "
                             "(default: https://example.com)")
    parser.add_argument("--no-verify", action="store_true",
                        help="Skip the smoke-test comparison")
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parent.parent
    source = Path(args.source)
    if not source.is_absolute():
        source = (Path.cwd() / source).resolve()
    if not source.is_file() or source.suffix != ".py":
        print(f"error: not a Python file: {args.source}")
        return 2

    target = build(source, repo_root / args.out)
    print(f"protected copy: {target}")
    print(f"  source: {source.stat().st_size:,} bytes "
          f"-> bytecode: {target.stat().st_size:,} bytes (docstrings stripped)")
    print(f"  run it with: python3 {target}")

    if args.no_verify:
        return 0
    smoke_args = shlex.split(args.smoke)
    print(f"verifying with: {' '.join(smoke_args)} ...")
    return 0 if verify(source, target, smoke_args, Path.cwd()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
