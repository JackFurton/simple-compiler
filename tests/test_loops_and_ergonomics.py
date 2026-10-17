#!/usr/bin/env python3

import sys
import shutil
import subprocess
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from compiler import Compiler, CompilerError
from interpreter import interpret_string
from tokens import TokenType

has_gcc = shutil.which("gcc") is not None or shutil.which("clang") is not None


def run_vm(source: str) -> list:
    out = []
    compiler = Compiler(output_callback=out.append)
    compiler.run(source)
    return [str(x) for x in out]


def run_interp(source: str) -> list:
    out = []
    interpret_string(source, output_callback=out.append)
    return [str(int(x) if isinstance(x, float) and x.is_integer() else x) for x in out]


def run_native(source: str, tmp_base: str = "tmp_loop_test") -> list:
    compiler = Compiler()
    c_file = f"{tmp_base}.c"
    bin_file = f"./{tmp_base}"

    c_code = compiler.transpile_to_c(source)
    with open(c_file, "w", encoding="utf-8") as f:
        f.write(c_code)

    cc = shutil.which("gcc") or shutil.which("clang") or "gcc"
    res = subprocess.run([cc, c_file, "-o", bin_file, "-lm"], capture_output=True, text=True)
    if res.returncode != 0:
        Path(c_file).unlink(missing_ok=True)
        raise RuntimeError(f"C build failed: {res.stderr}")

    try:
        proc = subprocess.run([bin_file], capture_output=True, text=True, check=True)
        lines = [line for line in proc.stdout.splitlines()]
    finally:
        Path(c_file).unlink(missing_ok=True)
        Path(bin_file).unlink(missing_ok=True)

    return lines


def test_compound_assignment_tokens():
    compiler = Compiler()
    tokens = compiler.tokenize("x += 1; y -= 2; z *= 3; w /= 4; for (item in items) { break; continue; }")
    types = [t.type for t in tokens]
    assert TokenType.PLUS_ASSIGN in types
    assert TokenType.MINUS_ASSIGN in types
    assert TokenType.STAR_ASSIGN in types
    assert TokenType.SLASH_ASSIGN in types
    assert TokenType.IN in types
    assert TokenType.BREAK in types
    assert TokenType.CONTINUE in types


def test_compound_assignments_across_targets():
    source = """
    let x = 10;
    x += 5;
    x -= 3;
    x *= 2;
    print x;

    let s = "Hello";
    s += " World";
    print s;

    let arr = [10, 20, 30];
    arr[1] += 100;
    arr[2] *= 2;
    print arr[1];
    print arr[2];

    let d = {"score": 50};
    d["score"] += 25;
    print d["score"];

    class Wallet {
        init(balance) {
            this.balance = balance;
        }
        deposit(amount) {
            this.balance += amount;
        }
        withdraw(amount) {
            this.balance -= amount;
        }
    }

    let w = Wallet(100);
    w.deposit(40);
    w.withdraw(15);
    print w.balance;
    """
    expected = ["24", "Hello World", "120", "60", "75", "125"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_compound") == expected


def test_while_break_and_continue_with_locals():
    source = """
    let i = 0;
    let sum = 0;
    while (i < 10) {
        i += 1;
        let step_val = i * 10;
        if (i == 3 or i == 5) {
            let skipped = true;
            continue;
        }
        if (i > 7) {
            let done = true;
            break;
        }
        sum += step_val;
    }
    print sum;
    print i;
    """
    # i=1 (10) + i=2 (20) + i=4 (40) + i=6 (60) + i=7 (70) = 200, stops at i=8
    expected = ["200", "8"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_while_bc") == expected


def test_for_loop_continue_runs_increment():
    source = """
    let out = "";
    for (let i = 0; i < 6; i += 1) {
        let local_copy = i;
        if (local_copy % 2 == 0) {
            continue;
        }
        out += str(local_copy) + ",";
    }
    print out;
    """
    expected = ["1,3,5,"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_for_cont") == expected


def test_for_in_list_and_string():
    source = """
    let nums = [10, 20, 30, 40, 50];
    let total = 0;
    for (n in nums) {
        if (n == 20) {
            continue;
        }
        if (n == 50) {
            break;
        }
        total += n;
    }
    print total;

    let chars = "";
    for ch in "abc" {
        chars += ch + "-";
    }
    print chars;
    """
    expected = ["80", "a-b-c-"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_for_in") == expected


def test_nested_for_in_with_break_and_continue():
    source = """
    let matrix = [[1, 2, 3], [4, 5, 6], [7, 8, 9]];
    let sum = 0;
    for (row in matrix) {
        for (val in row) {
            if (val == 2) {
                continue;
            }
            if (val == 6) {
                break;
            }
            sum += val;
        }
    }
    print sum;
    """
    # Row 1: 1 + 3 = 4
    # Row 2: 4 + 5 (breaks on 6) = 9
    # Row 3: 7 + 8 + 9 = 24
    # Total = 37
    expected = ["37"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_nested_for_in") == expected


def test_break_or_continue_outside_loop_is_compile_error():
    compiler = Compiler()
    try:
        compiler.compile("break;")
        assert False, "Expected CompileError for break outside loop"
    except CompilerError as e:
        assert "Cannot use 'break' outside of a loop" in str(e)

    try:
        compiler.compile("continue;")
        assert False, "Expected CompileError for continue outside loop"
    except CompilerError as e:
        assert "Cannot use 'continue' outside of a loop" in str(e)


def run_all():
    print("Testing compound assignment & loop control tokens...")
    test_compound_assignment_tokens()

    print("Testing compound assignments (+=, -=, *=, /=) across variables, indices, and properties...")
    test_compound_assignments_across_targets()

    print("Testing break and continue in while loops with scoped locals...")
    test_while_break_and_continue_with_locals()

    print("Testing continue in C-style for loops executes increment clause...")
    test_for_loop_continue_runs_increment()

    print("Testing for (x in iterable) over lists and strings...")
    test_for_in_list_and_string()

    print("Testing nested for-in loops with inner break and continue...")
    test_nested_for_in_with_break_and_continue()

    print("Testing compile-time error for break/continue outside loops...")
    test_break_or_continue_outside_loop_is_compile_error()

    print("All loop control and ergonomics tests passed!")


if __name__ == "__main__":
    run_all()
