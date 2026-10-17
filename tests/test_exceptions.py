#!/usr/bin/env python3

import sys
import shutil
import subprocess
from pathlib import Path

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from compiler import Compiler, CompilerError
from interpreter import interpret_string, RuntimeError as InterpRuntimeError
from tokens import TokenType

has_gcc = shutil.which("gcc") is not None or shutil.which("clang") is not None


def run_vm(source: str) -> list:
    out = []
    compiler = Compiler(output_callback=out.append)
    compiler.run(source)
    return out


def run_interp(source: str) -> list:
    out = []
    interpret_string(source, output_callback=out.append)
    return out


def run_native(source: str, tmp_base: str = "tmp_exc_test") -> list:
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


def test_lexer_and_parser():
    compiler = Compiler()
    tokens = compiler.tokenize("try { throw 1; } catch (e) { print e; }")
    token_types = [t.type for t in tokens]
    assert TokenType.TRY in token_types
    assert TokenType.THROW in token_types
    assert TokenType.CATCH in token_types

    ast = compiler.parse("try { throw \"boom\"; } catch (err) { print err; }")
    assert "TryCatch" in str(ast)
    assert "Throw" in str(ast)

    # Also test catch without parens and catch without variable
    ast2 = compiler.parse("try { throw 42; } catch e { print e; }")
    assert "catch (e)" in str(ast2)
    ast3 = compiler.parse("try { throw 42; } catch { print \"caught\"; }")
    assert "TryCatch" in str(ast3)


def test_basic_try_catch_throw():
    source = """
    try {
        print "before throw";
        throw "something went wrong";
        print "unreachable";
    } catch (e) {
        print "caught: " + e;
    }
    print "after try-catch";
    """
    expected = ["before throw", "caught: something went wrong", "after try-catch"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_exc_basic") == expected


def test_unwinding_across_nested_functions():
    source = """
    fn level3(x) {
        if (x < 0) {
            throw "negative input: " + str(x);
        }
        return x * 10;
    }

    fn level2(x) {
        let res = level3(x);
        print "level2 got " + str(res);
        return res + 1;
    }

    fn level1(x) {
        return level2(x);
    }

    try {
        print level1(5);
        print level1(-3);
        print "should not run";
    } catch (err) {
        print "handled from deep call: " + err;
    }
    """
    expected = ["level2 got 50", "51", "handled from deep call: negative input: -3"]
    assert [str(x) for x in run_vm(source)] == expected
    assert [str(x) for x in run_interp(source)] == expected
    if has_gcc:
        assert run_native(source, "tmp_exc_unwind") == expected


def test_nested_try_catch_and_rethrow():
    source = """
    try {
        try {
            throw "inner error";
        } catch (inner) {
            print "inner caught: " + inner;
            throw "rethrown: " + inner;
        }
    } catch (outer) {
        print "outer caught: " + outer;
    }
    """
    expected = ["inner caught: inner error", "outer caught: rethrown: inner error"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_exc_nested") == expected


def test_throwing_custom_objects_and_dicts():
    source = """
    class AppError {
        init(code, msg) {
            this.code = code;
            this.msg = msg;
        }
        describe() {
            return "[" + str(this.code) + "] " + this.msg;
        }
    }

    try {
        throw AppError(404, "User not found");
    } catch (err) {
        print err.describe();
    }

    try {
        throw {"status": 500, "reason": "Database timeout"};
    } catch (payload) {
        print str(payload["status"]) + ": " + payload["reason"];
    }
    """
    expected = ["[404] User not found", "500: Database timeout"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_exc_objects") == expected


def test_catching_runtime_errors():
    source = """
    let zero = 0;
    try {
        let x = 10 / zero;
        print x;
    } catch (e) {
        print "math error: " + e;
    }
    """
    expected = ["math error: Division by zero"]
    assert run_vm(source) == expected
    assert run_interp(source) == expected
    if has_gcc:
        assert run_native(source, "tmp_exc_divzero") == expected


def test_return_inside_try_cleans_up_handler():
    source = """
    fn compute(x) {
        try {
            if (x == 0) {
                throw "zero not allowed";
            }
            return 100 / x;
        } catch (e) {
            return -1;
        }
    }

    print compute(4);
    print compute(0);
    print compute(2);
    """
    vm_out = [int(x) for x in run_vm(source)]
    interp_out = [int(x) for x in run_interp(source)]
    assert vm_out == [25, -1, 50]
    assert interp_out == [25, -1, 50]
    if has_gcc:
        native_out = [int(float(x)) for x in run_native(source, "tmp_exc_return")]
        assert native_out == [25, -1, 50]


def test_uncaught_exception_raises_error():
    source = """
    fn bad() {
        throw "unhandled failure";
    }
    bad();
    """
    compiler = Compiler()
    try:
        compiler.run(source)
        assert False, "Expected CompilerError on uncaught exception"
    except CompilerError as e:
        assert "unhandled failure" in str(e)

    try:
        interpret_string(source)
        assert False, "Expected RuntimeError on uncaught exception in interpreter"
    except InterpRuntimeError as e:
        assert "unhandled failure" in str(e)


def test_disassembly_and_serialization_with_exceptions():
    source = """
    try {
        throw "test";
    } catch (e) {
        print e;
    }
    """
    compiler = Compiler()
    disasm = compiler.disassemble(source)
    assert "OP_PUSH_HANDLER" in disasm
    assert "OP_POP_HANDLER" in disasm
    assert "OP_THROW" in disasm


def run_all():
    print("Testing lexer and parser for try/catch/throw...")
    test_lexer_and_parser()

    print("Testing basic try/catch/throw...")
    test_basic_try_catch_throw()

    print("Testing stack unwinding across nested functions...")
    test_unwinding_across_nested_functions()

    print("Testing nested try/catch and re-throwing...")
    test_nested_try_catch_and_rethrow()

    print("Testing throwing custom class instances and dicts...")
    test_throwing_custom_objects_and_dicts()

    print("Testing catching built-in runtime errors (division by zero)...")
    test_catching_runtime_errors()

    print("Testing return inside try block handler cleanup...")
    test_return_inside_try_cleans_up_handler()

    print("Testing uncaught exception error reporting...")
    test_uncaught_exception_raises_error()

    print("Testing bytecode disassembly for exception opcodes...")
    test_disassembly_and_serialization_with_exceptions()

    print("All exception handling tests passed!")


if __name__ == "__main__":
    run_all()
