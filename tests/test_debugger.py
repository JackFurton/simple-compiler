#!/usr/bin/env python3

import sys
from pathlib import Path
from typing import List

src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from compiler import Compiler
from vm import VM
from debugger import Debugger, Breakpoint, DebuggerExit


class MockIO:
    """Helper to script input commands and capture debugger output."""
    def __init__(self, commands: List[str]):
        self.commands = list(commands)
        self.output: List[str] = []

    def input_fn(self, prompt: str = "") -> str:
        if not self.commands:
            return "continue"
        cmd = self.commands.pop(0)
        return cmd

    def output_fn(self, message: str = "") -> None:
        self.output.append(str(message))

    def get_output_text(self) -> str:
        return "\n".join(self.output)


def test_debugger_line_breakpoint():
    code = """
    let x = 10;
    let y = 20;
    let z = x + y;
    print z;
    """
    io = MockIO(["continue"])
    compiler = Compiler()
    debugger = Debugger(compiler.vm, source=code, filename="test.lang", input_fn=io.input_fn, output_fn=io.output_fn)
    compiler.vm.debugger = debugger

    bp = debugger.add_line_breakpoint(4)  # let z = x + y
    assert bp.id == 1
    assert bp.target == 4
    assert bp.hit_count == 0

    compiler.run(code)

    assert bp.hit_count == 1
    output_text = io.get_output_text()
    assert "Breakpoint #1 hit at line 4" in output_text


def test_debugger_function_breakpoint():
    code = """
    fn multiply(a, b) {
        return a * b;
    }
    let res = multiply(6, 7);
    print res;
    """
    io = MockIO(["continue"])
    compiler = Compiler()
    debugger = Debugger(compiler.vm, source=code, filename="test.lang", input_fn=io.input_fn, output_fn=io.output_fn)
    compiler.vm.debugger = debugger

    bp = debugger.add_function_breakpoint("multiply")
    assert bp.target == "multiply"

    compiler.run(code)

    assert bp.hit_count == 1
    output_text = io.get_output_text()
    assert "Breakpoint #1 hit at multiply()" in output_text


def test_debugger_stepi():
    code = """
    let a = 1;
    let b = 2;
    """
    # Pause at start, do 2 instruction steps, then continue
    io = MockIO(["stepi", "stepi", "continue"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn,
        pause_at_start=True
    )
    compiler.vm.debugger = debugger

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Paused at program entry" in output_text
    assert "Stepped to instruction at offset" in output_text


def test_debugger_step_into():
    code = """
    fn greet(name) {
        return "Hello " + name;
    }
    let msg = greet("Alice");
    """
    # Start paused at line 5 (let msg = greet("Alice")), step into greet
    io = MockIO(["step", "continue"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger
    debugger.add_line_breakpoint(5)

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Breakpoint #1 hit at line 5" in output_text
    # Should have stepped into function greet at line 2 or 3
    assert "Stepped to line 2" in output_text or "Stepped to line 3" in output_text


def test_debugger_next_step_over():
    code = """
    fn compute(x) {
        let a = x + 1;
        let b = a * 2;
        return b;
    }
    let result = compute(5);
    let done = 100;
    """
    # Break at line 7 (let result = compute(5)), 'next' should step over compute and pause at line 8
    io = MockIO(["next", "continue"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger
    debugger.add_line_breakpoint(7)

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Breakpoint #1 hit at line 7" in output_text
    assert "Stepped to line 8" in output_text


def test_debugger_finish_step_out():
    code = """
    fn worker() {
        let p = 1;
        let q = 2;
        return p + q;
    }
    let w = worker();
    let after = 42;
    """
    # Break at worker entry, 'finish' steps out to caller
    io = MockIO(["finish", "continue"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger
    debugger.add_function_breakpoint("worker")

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Breakpoint #1 hit at worker()" in output_text
    assert "Finished function" in output_text


def test_embedded_debugger_statement():
    code = """
    let val = 10;
    debugger;
    let next_val = val + 5;
    """
    io = MockIO(["print val", "continue"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Hit 'debugger;' statement at line 3" in output_text
    assert "val = (number) 10" in output_text


def test_debugger_inspection_commands():
    code = """
    fn test_scope(x, y) {
        let sum = x + y;
        debugger;
        return sum;
    }
    let global_var = "test_string";
    test_scope(15, 25);
    """
    io = MockIO([
        "stack",
        "frames",
        "locals",
        "globals",
        "print sum",
        "print global_var",
        "disasm",
        "list",
        "continue"
    ])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger

    compiler.run(code)

    output_text = io.get_output_text()
    assert "Hit 'debugger;' statement at line 4" in output_text
    # Stack inspection
    assert "Operand Stack" in output_text
    # Frames inspection
    assert "Call Stack" in output_text
    assert "test_scope()" in output_text
    # Locals inspection
    assert "Locals in frame 'test_scope'" in output_text
    assert "sum" in output_text
    assert "x" in output_text
    assert "y" in output_text
    # Globals inspection
    assert "Global Variables" in output_text
    assert "global_var" in output_text
    # Print commands
    assert "sum = (number) 40" in output_text
    assert "global_var = (string) 'test_string'" in output_text
    # Disassembly & list
    assert "Bytecode for test_scope()" in output_text
    assert "Source context" in output_text


def test_debugger_property_inspection():
    code = """
    class User {
        init(name, age) {
            this.name = name;
            this.age = age;
        }
    }
    let u = User("Alice", 30);
    debugger;
    """
    io = MockIO([
        "print u.name",
        "print u.age",
        "continue"
    ])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        filename="test.lang",
        input_fn=io.input_fn,
        output_fn=io.output_fn
    )
    compiler.vm.debugger = debugger

    compiler.run(code)

    output_text = io.get_output_text()
    assert "u.name = (string) 'Alice'" in output_text
    assert "u.age = (number) 30" in output_text


def test_debugger_breakpoint_management():
    compiler = Compiler()
    debugger = Debugger(compiler.vm)

    # Add breakpoints
    bp1 = debugger.add_line_breakpoint(10)
    bp2 = debugger.add_function_breakpoint("calculate")
    assert bp1.id == 1
    assert bp2.id == 2
    assert len(debugger.breakpoints) == 2

    # Remove breakpoint
    deleted = debugger.remove_breakpoint(1)
    assert deleted is True
    assert 1 not in debugger.breakpoints
    assert len(debugger.breakpoints) == 1

    # Remove non-existent
    deleted = debugger.remove_breakpoint(999)
    assert deleted is False

    # Clear all
    debugger.clear_breakpoints()
    assert len(debugger.breakpoints) == 0


def test_debugger_quit():
    code = """
    let a = 1;
    let b = 2;
    """
    io = MockIO(["quit"])
    compiler = Compiler()
    debugger = Debugger(
        compiler.vm,
        source=code,
        input_fn=io.input_fn,
        output_fn=io.output_fn,
        pause_at_start=True
    )
    compiler.vm.debugger = debugger

    # Quitting should terminate cleanly without throwing an unhandled exception
    res = compiler.run(code)
    assert res is None
    assert "Exiting debugger..." in io.get_output_text()


def test_debugger_cli_help_command():
    compiler = Compiler()
    io = MockIO(["help", "continue"])
    debugger = Debugger(
        compiler.vm,
        source="let x = 1;",
        input_fn=io.input_fn,
        output_fn=io.output_fn,
        pause_at_start=True
    )
    compiler.vm.debugger = debugger
    compiler.run("let x = 1;")
    output_text = io.get_output_text()
    assert "Simple Compiler Step-Debugger Commands:" in output_text
    assert "step, s" in output_text
    assert "break, b" in output_text


def run_all():
    print("Testing line breakpoints...")
    test_debugger_line_breakpoint()

    print("Testing function breakpoints...")
    test_debugger_function_breakpoint()

    print("Testing stepi (instruction step)...")
    test_debugger_stepi()

    print("Testing step into...")
    test_debugger_step_into()

    print("Testing next (step over)...")
    test_debugger_next_step_over()

    print("Testing finish (step out)...")
    test_debugger_finish_step_out()

    print("Testing embedded debugger; statement...")
    test_embedded_debugger_statement()

    print("Testing inspection commands...")
    test_debugger_inspection_commands()

    print("Testing property inspection...")
    test_debugger_property_inspection()

    print("Testing breakpoint management...")
    test_debugger_breakpoint_management()

    print("Testing debugger quit...")
    test_debugger_quit()

    print("Testing help command...")
    test_debugger_cli_help_command()

    print("All debugger tests passed!")


if __name__ == "__main__":
    run_all()
