#!/usr/bin/env python3

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from compiler import Compiler
from serializer import serialize_bytecode, deserialize_bytecode, MAGIC_HEADER
from vm import VM


def test_serialization_roundtrip():
    source = """
    fn power(base, exp) {
        let res = 1;
        let i = 0;
        while (i < exp) {
            res = res * base;
            i = i + 1;
        }
        return res;
    }
    let ans = power(2, 8);
    print ans;
    """
    c = Compiler()
    fn = c.compile(source)

    data = serialize_bytecode(fn)
    assert data.startswith(MAGIC_HEADER)

    deserialized_fn = deserialize_bytecode(data)
    assert deserialized_fn.name == fn.name

    out = []
    vm = VM(out.append)
    vm.interpret(deserialized_fn)
    assert out == [256]


def test_compile_to_file_and_run():
    source = "let val = 42 * 2; print val;"
    c = Compiler()

    with tempfile.NamedTemporaryFile(suffix=".lang", delete=False) as src_file:
        src_file.write(source.encode('utf-8'))
        src_path = src_file.name

    out_file = None
    try:
        out_file = c.compile_to_file(src_path)
        assert Path(out_file).exists()

        out = []
        vm_compiler = Compiler(out.append)
        vm_compiler.run_file(out_file)
        assert out == [84]
    finally:
        Path(src_path).unlink(missing_ok=True)
        if out_file:
            Path(out_file).unlink(missing_ok=True)


def run_all():
    test_serialization_roundtrip()
    test_compile_to_file_and_run()
    print("All serializer tests passed!")


if __name__ == "__main__":
    run_all()
