#!/usr/bin/env python3

import sys
import shutil
import subprocess
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from compiler import Compiler
from c_transpiler import CTranspiler

has_gcc = shutil.which("gcc") is not None or shutil.which("clang") is not None


def compile_and_run_native(source: str, tmp_base: str = "tmp_test") -> str:
    compiler = Compiler()
    c_file = f"{tmp_base}.c"
    bin_file = f"./{tmp_base}"

    c_code = compiler.transpile_to_c(source)
    with open(c_file, "w", encoding="utf-8") as f:
        f.write(c_code)

    cc = shutil.which("gcc") or shutil.which("clang") or "gcc"
    res = subprocess.run([cc, c_file, "-o", bin_file, "-lm"], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"C build failed: {res.stderr}")

    try:
        proc = subprocess.run([bin_file], capture_output=True, text=True, check=True)
        output = proc.stdout
    finally:
        Path(c_file).unlink(missing_ok=True)
        Path(bin_file).unlink(missing_ok=True)

    return output


def run_vm_output(source: str) -> str:
    out = []
    compiler = Compiler(output_callback=out.append)
    compiler.run(source)
    return "\n".join(str(item) for item in out) + ("\n" if out else "")


def test_transpile_to_c_code():
    compiler = Compiler()
    source = "let x = 10; let y = 20; print x + y;"
    c_code = compiler.transpile_to_c(source)
    assert "int main(int argc, char** argv)" in c_code
    assert "val_print" in c_code
    assert "val_add" in c_code


def test_native_arithmetic_and_conditionals():
    if not has_gcc:
        return
    source = """
    let a = 15;
    let b = 4;
    print a + b;
    print a - b;
    print a * b;
    print a / b;
    print a % b;

    if (a > b) {
        print "a is greater";
    } else {
        print "b is greater";
    }
    """
    native_out = compile_and_run_native(source, "tmp_math")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_native_recursion():
    if not has_gcc:
        return
    source = """
    fn fib(n) {
        if (n <= 1) {
            return n;
        }
        return fib(n - 1) + fib(n - 2);
    }
    print fib(8);
    print fib(10);
    """
    native_out = compile_and_run_native(source, "tmp_fib")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_native_while_loops():
    if not has_gcc:
        return
    source = """
    let sum = 0;
    let i = 1;
    while (i <= 10) {
        sum = sum + i;
        i = i + 1;
    }
    print sum;
    """
    native_out = compile_and_run_native(source, "tmp_while")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_native_collections():
    if not has_gcc:
        return
    source = """
    let lst = [10, 20, 30];
    append(lst, 40);
    print len(lst);
    print lst[0];
    print lst[3];
    let p = pop(lst);
    print p;
    print len(lst);

    let d = {"name": "Charlie", "age": 28};
    print d["name"];
    print d["age"];
    print len(d);
    """
    native_out = compile_and_run_native(source, "tmp_collections")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_native_classes_and_methods():
    if not has_gcc:
        return
    source = """
    class Counter {
        init(start) {
            this.val = start;
        }

        increment(amount) {
            this.val = this.val + amount;
            return this.val;
        }
    }

    let c = Counter(100);
    print c.val;
    print c.increment(25);
    print c.increment(15);
    """
    native_out = compile_and_run_native(source, "tmp_classes")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_native_stdlib_math_and_file_io():
    if not has_gcc:
        return
    source = """
    print sqrt(25);
    print abs(-42);
    print min(10, 20);
    print max(10, 20);

    let test_file = "native_test_io.txt";
    write_file(test_file, "Hello from native C!");
    let content = read_file(test_file);
    print content;
    remove_file(test_file);
    """
    native_out = compile_and_run_native(source, "tmp_stdlib")
    vm_out = run_vm_output(source)
    assert native_out.strip() == vm_out.strip()


def test_cli_emit_c_and_build():
    if not has_gcc:
        return

    main_py = Path(__file__).parent.parent / "main.py"
    src_file = Path("tmp_cli_test.lang")
    src_file.write_text("fn double(x) { return x * 2; } print double(21);")

    c_file = Path("tmp_cli_test.c")
    bin_file = Path("tmp_cli_test_bin")

    try:
        # Test --emit-c
        res_emit = subprocess.run([sys.executable, str(main_py), "--emit-c", str(src_file), "-o", str(c_file)], capture_output=True, text=True)
        assert res_emit.returncode == 0
        assert c_file.exists()

        # Test --build
        res_build = subprocess.run([sys.executable, str(main_py), "--build", str(src_file), "-o", str(bin_file)], capture_output=True, text=True)
        assert res_build.returncode == 0
        assert bin_file.exists()

        # Execute built binary
        res_run = subprocess.run([f"./{bin_file}"], capture_output=True, text=True)
        assert res_run.returncode == 0
        assert res_run.stdout.strip() == "42"

    finally:
        src_file.unlink(missing_ok=True)
        c_file.unlink(missing_ok=True)
        bin_file.unlink(missing_ok=True)


def run_all():
    print("Testing C code emission...")
    test_transpile_to_c_code()

    if has_gcc:
        print("Testing native arithmetic and conditionals...")
        test_native_arithmetic_and_conditionals()

        print("Testing native recursion...")
        test_native_recursion()

        print("Testing native while loops...")
        test_native_while_loops()

        print("Testing native collections...")
        test_native_collections()

        print("Testing native classes and methods...")
        test_native_classes_and_methods()

        print("Testing native stdlib (math & file I/O)...")
        test_native_stdlib_math_and_file_io()

        print("Testing CLI flags (--emit-c and --build)...")
        test_cli_emit_c_and_build()

    print("All C transpiler and native build tests passed!")


if __name__ == "__main__":
    run_all()
