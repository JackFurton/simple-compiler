#!/usr/bin/env python3

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from opcodes import OpCode
from chunk import FunctionObject, ClosureObject, ObjUpvalue


def test_basic_closure():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn make_adder(x) {
        fn add(y) {
            return x + y;
        }
        return add;
    }

    let add5 = make_adder(5);
    let add10 = make_adder(10);

    print add5(3);
    print add10(3);
    print add5(7);
    """
    compiler.run(source)
    assert output == [8, 13, 12]


def test_counter_closure_mutation():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn make_counter() {
        let count = 0;
        fn counter() {
            count = count + 1;
            return count;
        }
        return counter;
    }

    let c1 = make_counter();
    print c1();
    print c1();
    print c1();

    let c2 = make_counter();
    print c2();
    print c1();
    print c2();
    """
    compiler.run(source)
    assert output == [1, 2, 3, 1, 4, 2]


def test_shared_upvalues():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn make_account(initial) {
        let balance = initial;
        fn deposit(amt) {
            balance = balance + amt;
            return balance;
        }
        fn withdraw(amt) {
            balance = balance - amt;
            return balance;
        }
        fn get_balance() {
            return balance;
        }
        return [deposit, withdraw, get_balance];
    }

    let acct = make_account(100);
    let dep = acct[0];
    let wth = acct[1];
    let bal = acct[2];

    print dep(50);
    print wth(30);
    print bal();
    """
    compiler.run(source)
    assert output == [150, 120, 120]


def test_nested_closures():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn outer(a) {
        fn middle(b) {
            fn inner(c) {
                return a + b + c;
            }
            return inner;
        }
        return middle;
    }

    let m = outer(10);
    let inn = m(20);
    print inn(30);
    """
    compiler.run(source)
    assert output == [60]


def test_block_scoped_upvalue_closing():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn block_closure() {
        let f = nil;
        {
            let x = "closed_block_val";
            fn getter() {
                return x;
            }
            f = getter;
        }
        return f();
    }

    print block_closure();
    """
    compiler.run(source)
    assert output == ["closed_block_val"]


def test_recursive_closure():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn make_factorial() {
        fn fact(n) {
            if (n <= 1) {
                return 1;
            }
            return n * fact(n - 1);
        }
        return fact;
    }

    let f = make_factorial();
    print f(5);
    print f(6);
    """
    compiler.run(source)
    assert output == [120, 720]


def test_closure_serialization():
    output = []
    compiler = Compiler(output.append)

    source = """
    fn make_scaler(factor) {
        fn scale(v) {
            return v * factor;
        }
        return scale;
    }

    let double_it = make_scaler(2);
    let triple_it = make_scaler(3);
    print double_it(21);
    print triple_it(10);
    """

    with tempfile.NamedTemporaryFile(suffix=".lang", mode="w", delete=False) as f:
        f.write(source)
        src_path = f.name

    compiled_path = None
    try:
        compiled_path = compiler.compile_to_file(src_path)
        compiler.vm.output_callback = output.append
        compiler.run_file(compiled_path)
        assert output == [42, 30]
    finally:
        if os.path.exists(src_path):
            os.remove(src_path)
        if compiled_path and os.path.exists(compiled_path):
            os.remove(compiled_path)


def test_closure_disassembly():
    compiler = Compiler()
    source = """
    fn outer() {
        let x = 10;
        fn inner() {
            return x;
        }
        return inner;
    }
    """
    disasm = compiler.disassemble(source)
    assert "OP_CLOSURE" in disasm
    assert "OP_GET_UPVALUE" in disasm
    assert "local 1" in disasm or "local" in disasm


def run_all():
    test_basic_closure()
    test_counter_closure_mutation()
    test_shared_upvalues()
    test_nested_closures()
    test_block_scoped_upvalue_closing()
    test_recursive_closure()
    test_closure_serialization()
    test_closure_disassembly()
    print("All closure tests passed!")


if __name__ == "__main__":
    run_all()
