#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from vm import VM, VMError


def test_vm_arithmetic_and_logic():
    output = []
    compiler = Compiler(output.append)

    source = """
    let a = (10 + 20) * 2 / 5;
    print a;
    let b = 17 % 5;
    print b;
    let c = not (10 < 5) and (3 != 4);
    print c;
    """
    compiler.run(source)
    assert output == [12.0, 2, True]


def test_vm_strings():
    output = []
    compiler = Compiler(output.append)

    source = """
    let greet = "Hello, " + "World!";
    print greet;
    let repeated = "abc" * 3;
    print repeated;
    """
    compiler.run(source)
    assert output == ["Hello, World!", "abcabcabc"]


def test_vm_functions_and_recursion():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn factorial(n) {
        if (n <= 1) {
            return 1;
        }
        return n * factorial(n - 1);
    }
    print factorial(5);
    print factorial(6);
    """
    compiler.run(source)
    assert output == [120, 720]


def test_vm_loops():
    output = []
    compiler = Compiler(output.append)

    source = """
    let sum = 0;
    for (let i = 1; i <= 5; i = i + 1) {
        sum = sum + i;
    }
    print sum;
    """
    compiler.run(source)
    assert output == [15]


def test_vm_builtins():
    output = []
    compiler = Compiler(output.append)

    source = """
    let s = "testing";
    print len(s);
    print int("42") + 8;
    print type(s);
    print type(123);
    print type(true);
    """
    compiler.run(source)
    assert output == [7, 50, "string", "number", "bool"]


def test_vm_errors():
    compiler = Compiler(lambda _: None)

    # Division by zero
    try:
        compiler.run("let x = 10 / 0;")
        assert False, "Should have raised division by zero"
    except Exception as e:
        assert "Division by zero" in str(e)

    # Undefined variable
    try:
        compiler.run("print unknown_variable;")
        assert False, "Should have raised undefined variable"
    except Exception as e:
        assert "Undefined variable" in str(e)


def run_all():
    test_vm_arithmetic_and_logic()
    test_vm_strings()
    test_vm_functions_and_recursion()
    test_vm_loops()
    test_vm_builtins()
    test_vm_errors()
    print("All VM tests passed!")


if __name__ == "__main__":
    run_all()
