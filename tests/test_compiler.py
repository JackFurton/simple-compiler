#!/usr/bin/env python3

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from opcodes import OpCode
from chunk import FunctionObject


def test_compiler_bytecode_generation():
    compiler = Compiler()
    source = "let a = 5; let b = a + 10;"
    fn = compiler.compile(source)
    assert isinstance(fn, FunctionObject)

    # Inspect chunk
    chunk = fn.chunk
    opcodes = [OpCode(byte) for i, byte in enumerate(chunk.code) if i % 3 == 0]
    assert OpCode.OP_CONSTANT in opcodes
    assert OpCode.OP_DEFINE_GLOBAL in opcodes


def test_compiler_local_resolution():
    compiler = Compiler()
    source = """
    fn scope_test() {
        let x = 100;
        {
            let y = 200;
            return x + y;
        }
    }
    """
    fn = compiler.compile(source)
    chunk = fn.chunk
    # The compiled function should be in constants
    nested_fn = chunk.constants[0]
    assert isinstance(nested_fn, FunctionObject)
    assert nested_fn.name == "scope_test"

    # In nested function chunk, OP_GET_LOCAL should be emitted
    nested_opcodes = [OpCode(byte) for byte in nested_fn.chunk.code if byte in [int(o) for o in OpCode]]
    assert OpCode.OP_GET_LOCAL in nested_opcodes


def test_compiler_disassembly():
    compiler = Compiler()
    source = "let x = 42; print x;"
    disasm = compiler.disassemble(source)
    assert "OP_DEFINE_GLOBAL" in disasm
    assert "OP_PRINT" in disasm
    assert "OP_RETURN" in disasm


def run_all():
    test_compiler_bytecode_generation()
    test_compiler_local_resolution()
    test_compiler_disassembly()
    print("All compiler tests passed!")


if __name__ == "__main__":
    run_all()
