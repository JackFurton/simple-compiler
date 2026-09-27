#!/usr/bin/env python3

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from opcodes import OpCode
from chunk import ClassObject, InstanceObject, BoundMethod


def test_class_declaration_and_instantiation():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Point {
        fn init(x, y) {
            this.x = x;
            this.y = y;
        }

        fn distance_squared() {
            return this.x * this.x + this.y * this.y;
        }
    }

    let p = Point(3, 4);
    print p.x;
    print p.y;
    print p.distance_squared();

    p.x = 6;
    p.y = 8;
    print p.distance_squared();
    """
    compiler.run(source)
    assert output == [3, 4, 25, 100]


def test_empty_class_and_fields():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Bag {}

    let b = Bag();
    b.item = "gold coin";
    b.count = 42;

    print b.item;
    print b.count;
    """
    compiler.run(source)
    assert output == ["gold coin", 42]


def test_bound_method_references():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Greeter {
        fn init(name) {
            this.name = name;
        }

        fn greet(target) {
            return "Hello " + target + ", I am " + this.name;
        }
    }

    let g = Greeter("Bob");
    let greeter_func = g.greet;
    print greeter_func("Alice");
    """
    compiler.run(source)
    assert output == ["Hello Alice, I am Bob"]


def test_inheritance_and_polymorphism():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Shape {
        fn area() {
            return 0;
        }
    }

    class Rectangle < Shape {
        fn init(w, h) {
            this.w = w;
            this.h = h;
        }

        fn area() {
            return this.w * this.h;
        }
    }

    class Square < Rectangle {
        fn init(side) {
            this.w = side;
            this.h = side;
        }
    }

    let rect = Rectangle(4, 5);
    let sq = Square(7);

    print rect.area();
    print sq.area();
    """
    compiler.run(source)
    assert output == [20, 49]


def test_super_method_calls():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Pastry {
        fn describe() {
            return "pastry";
        }
    }

    class Doughnut < Pastry {
        fn describe() {
            return "glazed " + super.describe();
        }
    }

    class BostonCream < Doughnut {
        fn describe() {
            return "custard-filled " + super.describe();
        }
    }

    let bc = BostonCream();
    print bc.describe();
    """
    compiler.run(source)
    assert output == ["custard-filled glazed pastry"]


def test_closure_capturing_this():
    output = []
    compiler = Compiler(output.append)

    source = """
    class Counter {
        fn init() {
            this.count = 0;
        }

        fn get_stepper(step) {
            fn step_func() {
                this.count = this.count + step;
                return this.count;
            }
            return step_func;
        }
    }

    let c = Counter();
    let step5 = c.get_stepper(5);
    print step5();
    print step5();
    print step5();
    print c.count;
    """
    compiler.run(source)
    assert output == [5, 10, 15, 15]


def test_class_serialization():
    output = []
    compiler = Compiler(output.append)

    source = """
    class MathBox {
        fn init(multiplier) {
            this.multiplier = multiplier;
        }

        fn multiply(val) {
            return val * this.multiplier;
        }
    }

    let box = MathBox(10);
    print box.multiply(5);
    print box.multiply(8);
    """

    with tempfile.NamedTemporaryFile(suffix=".lang", mode="w", delete=False) as f:
        f.write(source)
        src_path = f.name

    compiled_path = None
    try:
        compiled_path = compiler.compile_to_file(src_path)
        compiler.vm.output_callback = output.append
        compiler.run_file(compiled_path)
        assert output == [50, 80]
    finally:
        if os.path.exists(src_path):
            os.remove(src_path)
        if compiled_path and os.path.exists(compiled_path):
            os.remove(compiled_path)


def test_class_errors():
    compiler = Compiler()

    # 1. 'this' outside of class method
    try:
        compiler.compile("print this;")
        assert False, "Should raise CompileError"
    except Exception as e:
        assert "Cannot use 'this' outside" in str(e)

    # 2. 'super' outside of class method
    try:
        compiler.compile("print super.foo();")
        assert False, "Should raise CompileError"
    except Exception as e:
        assert "Cannot use 'super' outside" in str(e)

    # 3. Initializer returning a value
    try:
        compiler.compile("class Bad { fn init() { return 10; } }")
        assert False, "Should raise CompileError"
    except Exception as e:
        assert "Cannot return a value from an initializer" in str(e)

    # 4. Class inheriting from itself
    try:
        compiler.compile("class SelfRef < SelfRef {}")
        assert False, "Should raise CompileError"
    except Exception as e:
        assert "cannot inherit from itself" in str(e)

    # 5. Accessing property on non-instance
    try:
        compiler.run("let x = 42; print x.item;")
        assert False, "Should raise VMError"
    except Exception as e:
        assert "Only instances have properties" in str(e)

    # 6. Undefined property access
    try:
        compiler.run("class Foo {} let f = Foo(); print f.bar;")
        assert False, "Should raise VMError"
    except Exception as e:
        assert "Undefined property" in str(e)


def run_all():
    test_class_declaration_and_instantiation()
    test_empty_class_and_fields()
    test_bound_method_references()
    test_inheritance_and_polymorphism()
    test_super_method_calls()
    test_closure_capturing_this()
    test_class_serialization()
    test_class_errors()
    print("All class and OOP tests passed!")


if __name__ == "__main__":
    run_all()
